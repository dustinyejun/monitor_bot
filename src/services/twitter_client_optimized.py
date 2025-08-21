"""
优化版Twitter API客户端
针对网络延迟进行优化
"""

import asyncio
import aiohttp
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
import json
from datetime import datetime

from ..config.settings import settings
from ..utils.logger import logger
from .twitter_client import TwitterUserInfo, TwitterTweetInfo, TwitterAPIError


class OptimizedTwitterClient:
    """优化版Twitter API客户端"""
    
    BASE_URL = "https://api.twitter.com/2"
    
    def __init__(self, bearer_token: str = None):
        self.bearer_token = bearer_token or settings.TWITTER_BEARER_TOKEN
        if not self.bearer_token:
            raise ValueError("Twitter Bearer Token 未配置")
        
        self.session = None
        self.rate_limit_remaining = 100
        self.rate_limit_reset = None
        
    async def __aenter__(self):
        """异步上下文管理器入口 - 优化连接配置"""
        # 优化连接配置
        timeout = aiohttp.ClientTimeout(total=10, connect=5)  # 降低超时时间
        connector = aiohttp.TCPConnector(
            limit=10,  # 连接池大小
            ttl_dns_cache=300,  # DNS缓存5分钟
            use_dns_cache=True,
        )
        
        self.session = aiohttp.ClientSession(
            headers={
                "Authorization": f"Bearer {self.bearer_token}",
                "Content-Type": "application/json",
                "User-Agent": "MonitorBot/1.0"
            },
            timeout=timeout,
            connector=connector
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
        retries: int = 2  # 减少重试次数
    ) -> Dict[str, Any]:
        """优化版API请求"""
        if not self.session:
            raise TwitterAPIError("TwitterClient未初始化，请使用async with语句")
            
        url = f"{self.BASE_URL}/{endpoint}"
        
        # 简化速率限制检查 - 只在真正需要时检查
        if self.rate_limit_remaining <= 1:
            if self.rate_limit_reset:
                wait_time = max(0, self.rate_limit_reset - datetime.now().timestamp())
                if wait_time > 0:
                    logger.warning(f"速率限制，等待 {wait_time:.1f} 秒")
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
                    if response.status == 200:
                        response_data = await response.json()
                        logger.debug(f"API请求成功: {endpoint}")
                        return response_data
                        
                    elif response.status == 429:
                        # 速率限制 - 更短的等待时间
                        if attempt < retries:
                            wait_time = 30 * (2 ** attempt)  # 减少等待时间
                            logger.warning(f"遇到速率限制，等待 {wait_time} 秒后重试")
                            await asyncio.sleep(wait_time)
                            continue
                        else:
                            raise TwitterAPIError(
                                f"速率限制，已达最大重试次数",
                                status_code=429
                            )
                            
                    elif response.status >= 400:
                        response_data = await response.json()
                        error_msg = f"API请求失败: {response.status}"
                        if 'errors' in response_data:
                            error_details = response_data['errors'][0].get('message', '')
                            error_msg += f" - {error_details}"
                            
                        raise TwitterAPIError(
                            error_msg,
                            status_code=response.status,
                            error_data=response_data
                        )
                        
            except asyncio.TimeoutError:
                if attempt < retries:
                    wait_time = 2 * (2 ** attempt)  # 更短的重试间隔
                    logger.warning(f"请求超时，{wait_time}秒后重试")
                    await asyncio.sleep(wait_time)
                    continue
                else:
                    raise TwitterAPIError("请求超时，已达最大重试次数")
                    
            except aiohttp.ClientError as e:
                if attempt < retries:
                    wait_time = 2 * (2 ** attempt)  # 更短的重试间隔
                    logger.warning(f"网络错误，{wait_time}秒后重试: {str(e)}")
                    await asyncio.sleep(wait_time)
                    continue
                else:
                    raise TwitterAPIError(f"网络请求失败: {str(e)}")
                    
        raise TwitterAPIError("所有重试均失败")
        
    # 其他方法保持不变，只是使用优化的_make_request
    async def get_user_by_username(self, username: str) -> Optional[TwitterUserInfo]:
        """根据用户名获取用户信息"""
        try:
            params = {
                "user.fields": "id,name,username,public_metrics"  # 减少字段以提高速度
            }
            
            response = await self._make_request(f"users/by/username/{username}", params)
            
            if 'data' not in response:
                return None
                
            user_data = response['data']
            return TwitterUserInfo(
                id=user_data['id'],
                username=user_data['username'],
                name=user_data['name'],
                public_metrics=user_data.get('public_metrics', {}),
                created_at=user_data.get('created_at', '')
            )
            
        except TwitterAPIError as e:
            logger.error(f"获取用户信息失败 {username}: {e.message}")
            if e.status_code == 404:
                return None
            raise
            
    def get_rate_limit_status(self) -> Dict[str, Any]:
        """获取当前速率限制状态"""
        return {
            "remaining": self.rate_limit_remaining,
            "reset_time": self.rate_limit_reset,
            "reset_datetime": datetime.fromtimestamp(self.rate_limit_reset) if self.rate_limit_reset else None
        }