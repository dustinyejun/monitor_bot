"""
推特监控服务
负责定时检查推特用户的新推文，分析内容并存储到数据库
"""

import asyncio
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from sqlalchemy import select, and_

from ..config.database import get_db
from ..models.twitter import TwitterUser, Tweet
from ..schemas.twitter import TwitterUserCreate, TwitterUserResponse
from .twitter_client import TwitterClient, TwitterAPIError
from .twitter_analyzer import TwitterAnalyzer, AnalysisResult
from ..utils.logger import logger


class TwitterMonitorService:
    """推特监控服务"""
    
    def __init__(self):
        self.twitter_client = None
        self.analyzer = TwitterAnalyzer()
        
    async def start_monitoring(self):
        """启动监控服务"""
        logger.info("启动推特监控服务")
        
        async with TwitterClient() as client:
            self.twitter_client = client
            
            while True:
                try:
                    await self.check_all_users()
                    await asyncio.sleep(60)  # 每分钟检查一次
                except Exception as e:
                    logger.error(f"监控循环出错: {str(e)}")
                    await asyncio.sleep(30)  # 出错后等待30秒再继续
                    
    async def check_all_users(self):
        """检查所有激活用户的新推文"""
        with get_db() as db:
            # 获取所有激活的用户
            active_users = db.execute(
                select(TwitterUser).where(TwitterUser.is_active == True)
            ).scalars().all()
            
            logger.info(f"开始检查 {len(active_users)} 个用户")
            
            for user in active_users:
                try:
                    await self.check_user_tweets(db, user)
                except Exception as e:
                    logger.error(f"检查用户 {user.username} 失败: {str(e)}")
                    
                # 避免API限制，用户间添加延迟
                await asyncio.sleep(2)
                
    async def check_user_tweets(self, db: Session, user: TwitterUser):
        """
        检查单个用户的新推文
        
        Args:
            db: 数据库会话
            user: 推特用户对象
        """
        try:
            # 如果用户没有twitter_id，先获取用户信息
            if not user.twitter_id:
                user_info = await self.twitter_client.get_user_by_username(user.username)
                if not user_info:
                    logger.warning(f"用户不存在: {user.username}")
                    # 将用户标记为非活跃
                    user.is_active = False
                    db.commit()
                    return
                    
                # 更新用户信息
                user.twitter_id = user_info.id
                user.display_name = user_info.name
                db.commit()
                
            # 获取新推文
            since_id = user.last_tweet_id
            tweets = await self.twitter_client.get_user_tweets(
                user_id=user.twitter_id,
                since_id=since_id,
                max_results=50
            )
            
            if not tweets:
                logger.debug(f"用户 {user.username} 没有新推文")
                user.last_check_at = datetime.now(timezone.utc).isoformat()
                db.commit()
                return
                
            logger.info(f"用户 {user.username} 发现 {len(tweets)} 条新推文")
            
            # 处理推文
            new_tweets_count = 0
            ca_tweets_count = 0
            
            for tweet_info in tweets:
                # 检查推文是否已存在
                existing_tweet = db.execute(
                    select(Tweet).where(Tweet.tweet_id == tweet_info.id)
                ).scalar_one_or_none()
                
                if existing_tweet:
                    continue
                    
                # 分析推文内容
                analysis_result = self.analyzer.analyze_tweet(tweet_info.text)
                
                # 创建推文记录
                tweet = Tweet(
                    tweet_id=tweet_info.id,
                    user_id=user.id,
                    content=tweet_info.text,
                    tweet_url=f"https://twitter.com/{user.username}/status/{tweet_info.id}",
                    ca_addresses=self.analyzer.get_ca_addresses_as_strings(analysis_result) if analysis_result.has_ca else None,
                    is_processed=False,
                    is_notified=False,
                    like_count=tweet_info.public_metrics.get('like_count', 0),
                    retweet_count=tweet_info.public_metrics.get('retweet_count', 0),
                    reply_count=tweet_info.public_metrics.get('reply_count', 0),
                    tweet_created_at=tweet_info.created_at
                )
                
                db.add(tweet)
                new_tweets_count += 1
                
                if analysis_result.has_ca:
                    ca_tweets_count += 1
                    logger.info(f"发现包含CA地址的推文: {user.username} - {len(analysis_result.ca_addresses)} 个地址")
                    
                # 更新最新推文ID
                user.last_tweet_id = tweet_info.id
                
            # 更新检查时间
            user.last_check_at = datetime.now(timezone.utc).isoformat()
            
            # 提交所有更改
            db.commit()
            
            logger.info(f"用户 {user.username} 处理完成: 新推文 {new_tweets_count}, CA推文 {ca_tweets_count}")
            
        except TwitterAPIError as e:
            logger.error(f"Twitter API错误 {user.username}: {e.message}")
            if e.status_code == 404:
                # 用户不存在或被删除
                user.is_active = False
                db.commit()
        except Exception as e:
            logger.error(f"处理用户 {user.username} 时出错: {str(e)}")
            db.rollback()
            
    def add_user(self, username: str, display_name: str = None) -> TwitterUserResponse:
        """
        添加新的监控用户
        
        Args:
            username: 推特用户名（不含@）
            display_name: 显示名称
            
        Returns:
            创建的用户对象
        """
        with get_db() as db:
            # 检查用户是否已存在
            existing_user = db.execute(
                select(TwitterUser).where(TwitterUser.username == username.lower())
            ).scalar_one_or_none()
            
            if existing_user:
                logger.warning(f"用户已存在: {username}")
                return TwitterUserResponse.model_validate(existing_user)
                
            # 创建新用户
            user = TwitterUser(
                username=username.lower(),
                display_name=display_name,
                is_active=True
            )
            
            db.add(user)
            db.commit()
            db.refresh(user)
            
            logger.info(f"添加新用户: {username}")
            return TwitterUserResponse.model_validate(user)
            
    def remove_user(self, username: str) -> bool:
        """
        移除监控用户
        
        Args:
            username: 推特用户名
            
        Returns:
            是否成功移除
        """
        with get_db() as db:
            user = db.execute(
                select(TwitterUser).where(TwitterUser.username == username.lower())
            ).scalar_one_or_none()
            
            if not user:
                logger.warning(f"用户不存在: {username}")
                return False
                
            db.delete(user)
            db.commit()
            
            logger.info(f"移除用户: {username}")
            return True
            
    def update_user_status(self, username: str, is_active: bool) -> bool:
        """
        更新用户监控状态
        
        Args:
            username: 推特用户名
            is_active: 是否激活
            
        Returns:
            是否成功更新
        """
        with get_db() as db:
            user = db.execute(
                select(TwitterUser).where(TwitterUser.username == username.lower())
            ).scalar_one_or_none()
            
            if not user:
                logger.warning(f"用户不存在: {username}")
                return False
                
            user.is_active = is_active
            db.commit()
            
            status = "激活" if is_active else "停用"
            logger.info(f"{status}用户监控: {username}")
            return True
            
    def get_user_list(self, active_only: bool = False) -> List[TwitterUserResponse]:
        """
        获取用户列表
        
        Args:
            active_only: 是否只返回活跃用户
            
        Returns:
            用户列表
        """
        with get_db() as db:
            query = select(TwitterUser)
            if active_only:
                query = query.where(TwitterUser.is_active == True)
                
            users = db.execute(query).scalars().all()
            return [TwitterUserResponse.model_validate(user) for user in users]
            
    def get_unprocessed_ca_tweets(self, limit: int = 50) -> List[Dict[str, Any]]:
        """
        获取未处理的包含CA地址的推文
        
        Args:
            limit: 返回数量限制
            
        Returns:
            推文列表
        """
        with get_db() as db:
            tweets = db.execute(
                select(Tweet, TwitterUser)
                .join(TwitterUser, Tweet.user_id == TwitterUser.id)
                .where(
                    and_(
                        Tweet.ca_addresses.isnot(None),
                        Tweet.is_processed == False
                    )
                )
                .order_by(Tweet.created_at.desc())
                .limit(limit)
            ).all()
            
            result = []
            for tweet, user in tweets:
                result.append({
                    'tweet_id': tweet.tweet_id,
                    'content': tweet.content,
                    'tweet_url': tweet.tweet_url,
                    'ca_addresses': tweet.ca_addresses,
                    'username': user.username,
                    'display_name': user.display_name,
                    'created_at': tweet.created_at,
                    'like_count': tweet.like_count,
                    'retweet_count': tweet.retweet_count
                })
                
            return result
            
    def mark_tweets_processed(self, tweet_ids: List[str]):
        """
        标记推文为已处理
        
        Args:
            tweet_ids: 推文ID列表
        """
        with get_db() as db:
            db.execute(
                Tweet.__table__.update()
                .where(Tweet.tweet_id.in_(tweet_ids))
                .values(is_processed=True)
            )
            db.commit()
            
            logger.info(f"标记 {len(tweet_ids)} 条推文为已处理")
            
    def mark_tweets_notified(self, tweet_ids: List[str]):
        """
        标记推文为已通知
        
        Args:
            tweet_ids: 推文ID列表
        """
        with get_db() as db:
            db.execute(
                Tweet.__table__.update()
                .where(Tweet.tweet_id.in_(tweet_ids))
                .values(is_notified=True)
            )
            db.commit()
            
            logger.info(f"标记 {len(tweet_ids)} 条推文为已通知")
            
    def get_statistics(self) -> Dict[str, Any]:
        """
        获取监控统计信息
        
        Returns:
            统计数据
        """
        with get_db() as db:
            # 用户统计
            total_users = db.execute(select(TwitterUser)).scalars().all()
            active_users = [u for u in total_users if u.is_active]
            
            # 推文统计
            all_tweets = db.execute(select(Tweet)).scalars().all()
            ca_tweets = [t for t in all_tweets if t.ca_addresses]
            
            # 今日统计
            today = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
            today_tweets = [t for t in all_tweets if t.created_at >= today]
            today_ca_tweets = [t for t in ca_tweets if t.created_at >= today]
            
            return {
                'total_users': len(total_users),
                'active_users': len(active_users),
                'total_tweets': len(all_tweets),
                'ca_tweets': len(ca_tweets),
                'today_tweets': len(today_tweets),
                'today_ca_tweets': len(today_ca_tweets),
                'unprocessed_ca_tweets': len([t for t in ca_tweets if not t.is_processed]),
                'unnotified_ca_tweets': len([t for t in ca_tweets if not t.is_notified])
            }