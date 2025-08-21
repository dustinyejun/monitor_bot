"""
Twitter API 客户端
负责与Twitter API v2进行交互，获取用户信息和推文数据
"""

import asyncio
import aiohttp
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
import json
from datetime import datetime

from ..config.settings import settings
from ..utils.logger import logger


@dataclass
class TwitterUserInfo:
    """Twitter用户信息数据类"""
    id: str
    username: str
    name: str
    public_metrics: Dict[str, int]
    created_at: str
    description: Optional[str] = None
    profile_image_url: Optional[str] = None


@dataclass  
class TwitterTweetInfo:
    """Twitter推文信息数据类"""
    id: str
    text: str
    created_at: str
    public_metrics: Dict[str, int]
    author_id: str
    referenced_tweets: Optional[List[Dict]] = None
    entities: Optional[Dict] = None


class TwitterAPIError(Exception):
    """Twitter API异常"""
    def __init__(self, message: str, status_code: int = None, error_data: Dict = None):
        self.message = message
        self.status_code = status_code
        self.error_data = error_data or {}
        super().__init__(self.message)


class TwitterClient:
    """Twitter API客户端"""
    
    BASE_URL = "https://api.twitter.com/2"
    
    def __init__(self, bearer_token: str = None):
        """
        初始化Twitter客户端
        
        Args:
            bearer_token: Twitter Bearer Token，如果未提供则从配置获取
        """
        self.bearer_token = bearer_token or settings.TWITTER_BEARER_TOKEN
        if not self.bearer_token:
            raise ValueError("Twitter Bearer Token 未配置")
        
        self.session = None
        self.rate_limit_remaining = 100
        self.rate_limit_reset = None
        
    async def __aenter__(self):
        """异步上下文管理器入口"""
        self.session = aiohttp.ClientSession(
            headers={
                "Authorization": f"Bearer {self.bearer_token}",
                "Content-Type": "application/json"
            }
        )
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器退出"""
        if self.session:
            await self.session.close()
            
    async def _make_request(
        self, 
        endpoint: str, 
        params: Dict[str, Any] = None,
        retries: int = 3
    ) -> Dict[str, Any]:
        """
        发送API请求
        
        Args:
            endpoint: API端点
            params: 请求参数
            retries: 重试次数
            
        Returns:
            API响应数据
            
        Raises:
            TwitterAPIError: API请求失败
        """
        if not self.session:
            raise TwitterAPIError("TwitterClient未初始化，请使用async with语句")
            
        url = f"{self.BASE_URL}/{endpoint}"
        
        # 检查速率限制
        if self.rate_limit_remaining <= 2:  # 降低到2个请求时才等待
            if self.rate_limit_reset:
                wait_time = max(0, self.rate_limit_reset - datetime.now().timestamp())
                if wait_time > 0:
                    logger.warning(f"接近速率限制，等待 {wait_time:.1f} 秒")
                    await asyncio.sleep(wait_time)
        
        for attempt in range(retries + 1):
            try:
                async with self.session.get(url, params=params) as response:
                    # 更新速率限制信息
                    self.rate_limit_remaining = int(
                        response.headers.get('x-rate-limit-remaining', 0)
                    )
                    reset_time = response.headers.get('x-rate-limit-reset')
                    if reset_time:
                        self.rate_limit_reset = int(reset_time)
                    
                    # 处理响应
                    response_data = await response.json()
                    logger.info(f"API响应: {endpoint} - 状态: {response.status}")
                    
                    # 如果需要查看完整响应，取消下面这行的注释
                    logger.info(f"响应数据: {response_data}")
                    
                    if response.status == 200:
                        logger.info(f"API请求成功: {endpoint}")
                        return response_data
                        
                    elif response.status == 429:
                        # 速率限制
                        if attempt < retries:
                            wait_time = 60 * (2 ** attempt)  # 指数退避
                            logger.warning(f"遇到速率限制，等待 {wait_time} 秒后重试")
                            await asyncio.sleep(wait_time)
                            continue
                        else:
                            raise TwitterAPIError(
                                f"速率限制，已达最大重试次数",
                                status_code=429,
                                error_data=response_data
                            )
                            
                    elif response.status >= 400:
                        error_msg = f"API请求失败: {response.status}"
                        if 'errors' in response_data:
                            error_details = response_data['errors'][0].get('message', '')
                            error_msg += f" - {error_details}"
                            
                        raise TwitterAPIError(
                            error_msg,
                            status_code=response.status,
                            error_data=response_data
                        )
                        
            except aiohttp.ClientError as e:
                if attempt < retries:
                    wait_time = 5 * (2 ** attempt)
                    logger.warning(f"网络错误，{wait_time}秒后重试: {str(e)}")
                    await asyncio.sleep(wait_time)
                    continue
                else:
                    raise TwitterAPIError(f"网络请求失败: {str(e)}")
                    
        raise TwitterAPIError("所有重试均失败")
        
    async def get_user_by_username(self, username: str) -> Optional[TwitterUserInfo]:
        """
        根据用户名获取用户信息
        
        Args:
            username: Twitter用户名（不含@符号）
            
        Returns:
            用户信息，如果用户不存在则返回None
        """
        try:
            params = {
                "user.fields": "id,name,username,description,public_metrics,created_at,profile_image_url"
            }
            
            response = await self._make_request(f"users/by/username/{username}", params)
            
            if 'data' not in response:
                logger.warning(f"用户不存在: {username}")
                return None
                
            user_data = response['data']
            return TwitterUserInfo(
                id=user_data['id'],
                username=user_data['username'],
                name=user_data['name'],
                description=user_data.get('description'),
                public_metrics=user_data.get('public_metrics', {}),
                created_at=user_data.get('created_at'),
                profile_image_url=user_data.get('profile_image_url')
            )
            
        except TwitterAPIError as e:
            logger.error(f"获取用户信息失败 {username}: {e.message}")
            if e.status_code == 404:
                return None
            raise
            
    async def get_user_tweets(
        self, 
        user_id: str, 
        since_id: Optional[str] = None,
        max_results: int = 10
    ) -> List[TwitterTweetInfo]:
        """
        获取用户推文
        
        Args:
            user_id: Twitter用户ID  
            since_id: 获取此ID之后的推文
            max_results: 最大结果数 (5-100)
            
        Returns:
            推文列表
        """
        try:
            params = {
                "tweet.fields": "id,text,created_at,public_metrics,referenced_tweets,entities",
                "max_results": min(max(max_results, 5), 100)
            }
            
            if since_id:
                params["since_id"] = since_id
                
            response = await self._make_request(f"users/{user_id}/tweets", params)
            
            tweets = []
            if 'data' in response:
                for tweet_data in response['data']:
                    tweet = TwitterTweetInfo(
                        id=tweet_data['id'],
                        text=tweet_data['text'],
                        created_at=tweet_data['created_at'],
                        public_metrics=tweet_data.get('public_metrics', {}),
                        author_id=user_id,
                        referenced_tweets=tweet_data.get('referenced_tweets'),
                        entities=tweet_data.get('entities')
                    )
                    tweets.append(tweet)
                    
            logger.info(f"获取到 {len(tweets)} 条推文，用户: {user_id}")
            return tweets
            
        except TwitterAPIError as e:
            logger.error(f"获取用户推文失败 {user_id}: {e.message}")
            raise
            
    async def get_tweet_by_id(self, tweet_id: str) -> Optional[TwitterTweetInfo]:
        """
        根据推文ID获取推文详情
        
        Args:
            tweet_id: 推文ID
            
        Returns:
            推文信息，如果不存在则返回None
        """
        try:
            params = {
                "tweet.fields": "id,text,created_at,public_metrics,author_id,referenced_tweets,entities"
            }
            
            response = await self._make_request(f"tweets/{tweet_id}", params)
            
            if 'data' not in response:
                return None
                
            tweet_data = response['data']
            return TwitterTweetInfo(
                id=tweet_data['id'],
                text=tweet_data['text'],
                created_at=tweet_data['created_at'],
                public_metrics=tweet_data.get('public_metrics', {}),
                author_id=tweet_data['author_id'],
                referenced_tweets=tweet_data.get('referenced_tweets'),
                entities=tweet_data.get('entities')
            )
            
        except TwitterAPIError as e:
            logger.error(f"获取推文失败 {tweet_id}: {e.message}")
            if e.status_code == 404:
                return None
            raise
            
    def get_rate_limit_status(self) -> Dict[str, Any]:
        """
        获取当前速率限制状态
        
        Returns:
            速率限制信息
        """
        return {
            "remaining": self.rate_limit_remaining,
            "reset_time": self.rate_limit_reset,
            "reset_datetime": datetime.fromtimestamp(self.rate_limit_reset) if self.rate_limit_reset else None
        }