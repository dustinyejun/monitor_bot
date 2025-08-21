#!/usr/bin/env python3
"""
快速推特API连接测试
仅验证基本连接和获取一个用户信息
"""

import asyncio
import os
import sys
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent))

from src.services.twitter_client import TwitterClient, TwitterAPIError


async def quick_test():
    """快速测试推特API连接"""
    print("🔧 快速推特API连接测试")
    print("-" * 30)
    
    # 检查环境变量
    token = os.getenv('TWITTER_BEARER_TOKEN')
    if not token:
        print("❌ 未找到 TWITTER_BEARER_TOKEN 环境变量")
        print("请设置: export TWITTER_BEARER_TOKEN='你的token'")
        return False
        
    print(f"✅ 找到Bearer Token: {token[:10]}...")
    
    try:
        async with TwitterClient(token) as client:
            print("🔍 测试获取用户信息...")
            
            # 测试获取一个知名用户的信息
            user = await client.get_user_by_username("elonmusk")
            
            if user:
                print("🎉 API测试成功！")
                print(f"   用户: {user.name} (@{user.username})")
                print(f"   ID: {user.id}")
                print(f"   粉丝: {user.public_metrics.get('followers_count', 'N/A')}")
                
                # 检查速率限制
                rate_limit = client.get_rate_limit_status()
                print(f"   剩余请求: {rate_limit['remaining']}")
                
                return True
            else:
                print("❌ 无法获取用户信息")
                return False
                
    except TwitterAPIError as e:
        print(f"❌ API错误: {e.message}")
        if e.status_code == 401:
            print("   可能是Bearer Token无效")
        elif e.status_code == 429:
            print("   遇到速率限制，请稍后再试")
        return False
        
    except Exception as e:
        print(f"❌ 未知错误: {str(e)}")
        return False


if __name__ == "__main__":
    result = asyncio.run(quick_test())
    
    if result:
        print("\n✅ 推特API连接正常！可以继续使用完整功能。")
        print("运行完整测试: uv run python tests/test_real_twitter_api.py")
    else:
        print("\n❌ 推特API连接失败，请检查配置。")
        print("查看详细指南: cat 推特API测试指南.md")