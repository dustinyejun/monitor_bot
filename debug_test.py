#!/usr/bin/env python3
"""
启用DEBUG日志级别的API测试
"""

import asyncio
import os
import sys
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent))

# 临时设置DEBUG级别
os.environ['LOG_LEVEL'] = 'DEBUG'

from src.services.twitter_client import TwitterClient
from src.utils.logger import logger


async def debug_api_test():
    """使用DEBUG级别测试API"""
    print("🔧 DEBUG级别API测试")
    print("-" * 30)
    
    # 重新设置日志级别
    logger.remove()
    logger.add(
        sys.stdout,
        format="<green>{time:HH:mm:ss}</green> | <level>{level}</level> | <cyan>{name}</cyan> - <level>{message}</level>",
        level="DEBUG",
        colorize=True
    )
    
    token = os.getenv('TWITTER_BEARER_TOKEN')
    if not token:
        print("❌ 未找到 TWITTER_BEARER_TOKEN 环境变量")
        return
        
    logger.info("开始DEBUG级别API测试")
    
    try:
        async with TwitterClient(token) as client:
            logger.debug("Twitter客户端已初始化")
            
            user = await client.get_user_by_username("jack")
            
            if user:
                logger.info(f"✅ 成功获取用户: {user.name}")
                print(f"用户ID: {user.id}")
                print(f"用户名: @{user.username}")
                print(f"显示名: {user.name}")
            else:
                logger.warning("❌ 未能获取用户信息")
                
    except Exception as e:
        logger.error(f"测试失败: {str(e)}")


if __name__ == "__main__":
    asyncio.run(debug_api_test())