"""
Twitter监控插件
将Twitter监控功能封装为可插拔的监控插件
"""

from datetime import datetime
from typing import Dict, Any, List

from ..core.monitor_plugin import MonitorPlugin
from ..services.notification_engine import notification_engine
from ..services.twitter_analyzer import TwitterAnalyzer
from ..services.twitter_client import TwitterClient
from ..services.twitter_monitor import TwitterMonitorService
from ..utils.logger import logger


class TwitterMonitorPlugin(MonitorPlugin):
    """Twitter监控插件"""
    
    def __init__(self, name: str, config: Dict[str, Any] = None):
        super().__init__(name, config)
        self.twitter_client = None
        self.twitter_analyzer = None 
        self.twitter_monitor = None
        
    @property
    def check_interval(self) -> int:
        """检查间隔（秒）"""
        return self.get_config("check_interval", 60)
    
    async def initialize(self) -> bool:
        """初始化Twitter监控组件"""
        try:
            logger.info("初始化Twitter监控插件...")
            
            # 检查必要配置
            bearer_token = self.get_config("bearer_token")
            if not bearer_token:
                logger.error("Twitter Bearer Token未配置")
                return False
            
            # 初始化Twitter客户端
            self.twitter_client = TwitterClient(bearer_token)
            
            # 测试API连接
            if not await self._test_api_connection():
                logger.error("Twitter API连接测试失败")
                return False
            
            # 初始化分析器和监控服务
            self.twitter_analyzer = TwitterAnalyzer()
            self.twitter_monitor = TwitterMonitorService()
            
            logger.info("Twitter监控插件初始化成功")
            return True
            
        except Exception as e:
            logger.error(f"Twitter监控插件初始化失败: {str(e)}")
            return False
    
    async def _test_api_connection(self) -> bool:
        """测试API连接"""
        try:
            # 简单的API测试
            async with self.twitter_client as client:
                # 可以添加简单的API调用测试
                pass
            return True
        except Exception as e:
            logger.error(f"Twitter API连接测试失败: {str(e)}")
            return False
    
    async def check(self) -> bool:
        """执行Twitter监控检查"""
        try:
            logger.debug("执行Twitter监控检查...")
            
            # 获取需要监控的用户
            monitored_users = self.twitter_monitor.get_active_users()
            if not monitored_users:
                logger.debug("没有需要监控的Twitter用户")
                return True
            
            check_success = True
            processed_count = 0
            
            async with self.twitter_client as client:
                for user in monitored_users:
                    try:
                        # 获取用户最新推文
                        tweets = await client.get_user_tweets(
                            user.username,
                            max_results=10,
                            since_id=user.last_tweet_id
                        )
                        
                        if tweets:
                            # 分析推文
                            analyzed_tweets = []
                            for tweet in tweets:
                                analysis = await self.twitter_analyzer.analyze_tweet(tweet)
                                analyzed_tweets.append(analysis)
                            
                            # 处理分析结果
                            await self._process_analyzed_tweets(user, analyzed_tweets)
                            processed_count += len(analyzed_tweets)
                        
                        # 更新检查时间
                        await self.twitter_monitor.update_user_check_time(
                            user.username, 
                            datetime.now()
                        )
                        
                    except Exception as e:
                        logger.error(f"检查用户 {user.username} 失败: {str(e)}")
                        check_success = False
                        continue
            
            logger.info(f"Twitter监控检查完成，处理了 {processed_count} 条推文")
            return check_success
            
        except Exception as e:
            logger.error(f"Twitter监控检查失败: {str(e)}")
            return False
    
    async def _process_analyzed_tweets(self, user, analyzed_tweets: List[Any]):
        """处理分析后的推文"""
        try:
            # 筛选包含CA地址的高置信度推文
            ca_tweets = []
            for analysis in analyzed_tweets:
                if (analysis.ca_addresses and 
                    analysis.confidence_score >= 0.7):  # 高置信度阈值
                    ca_tweets.append(analysis)
            
            if ca_tweets:
                logger.info(f"发现 {len(ca_tweets)} 条包含CA地址的高质量推文")
                
                # 保存到数据库
                for analysis in ca_tweets:
                    await self.twitter_monitor.save_tweet_analysis(analysis)
                
                # 触发通知（如果需要）
                await self._trigger_notifications(user, ca_tweets)
                
        except Exception as e:
            logger.error(f"处理分析推文失败: {str(e)}")
    
    async def _trigger_notifications(self, user, ca_tweets: List[Any]):
        """触发通知"""
        try:
            for analysis in ca_tweets:
                # 准备通知数据
                notification_data = {
                    "username": user.username,
                    "display_name": user.display_name or user.username,
                    "content": analysis.content,
                    "ca_addresses": ", ".join(analysis.ca_addresses),
                    "tweet_url": f"https://twitter.com/{user.username}/status/{analysis.tweet_id}",
                    "tweet_created_at": analysis.created_at.strftime('%Y-%m-%d %H:%M:%S') if analysis.created_at else "未知",
                    "confidence_score": analysis.confidence_score,
                    "risk_score": analysis.risk_score
                }
                
                # 触发通知引擎检查规则
                await notification_engine.check_twitter_rules(notification_data)
                
                logger.info(f"发现重要推文: @{user.username} - {analysis.ca_addresses}")
                
        except Exception as e:
            logger.error(f"触发通知失败: {str(e)}")
    
    async def cleanup(self):
        """清理资源"""
        try:
            logger.info("清理Twitter监控插件资源...")
            
            if self.twitter_client:
                # Twitter客户端使用上下文管理器，无需特殊清理
                pass
            
            self.twitter_client = None
            self.twitter_analyzer = None
            self.twitter_monitor = None
            
            logger.info("Twitter监控插件资源清理完成")
            
        except Exception as e:
            logger.error(f"Twitter监控插件清理失败: {str(e)}")
    
    def get_plugin_info(self) -> Dict[str, Any]:
        """获取插件信息"""
        return {
            "name": self.name,
            "type": "twitter_monitor",
            "version": "1.0.0",
            "description": "监控指定Twitter用户的推文，识别CA地址和投资机会",
            "config": {
                "check_interval": self.check_interval,
                "bearer_token_configured": bool(self.get_config("bearer_token")),
            },
            "stats": {
                "status": self.stats.status.value,
                "total_checks": self.stats.total_checks,
                "success_rate": self.stats.success_rate,
                "uptime_seconds": self.stats.uptime_seconds,
            }
        }


# 注册插件
from ..core.monitor_plugin import plugin_registry
plugin_registry.register("twitter", TwitterMonitorPlugin)