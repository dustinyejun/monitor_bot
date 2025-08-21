#!/usr/bin/env python3
"""
轻量级推特API测试
仅进行最少的API调用来验证功能
"""

import asyncio
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from src.services.twitter_client import TwitterClient, TwitterAPIError


async def lightweight_test():
    """轻量级测试，最少API调用"""
    print("🧪 轻量级推特API测试")
    print("-" * 30)
    
    token = os.getenv('TWITTER_BEARER_TOKEN')
    if not token:
        print("❌ 未找到 TWITTER_BEARER_TOKEN 环境变量")
        return
        
    try:
        async with TwitterClient(token) as client:
            # 首先检查速率限制
            rate_limit = client.get_rate_limit_status()
            print(f"📊 当前剩余请求: {rate_limit['remaining']}")
            
            if rate_limit['remaining'] < 3:
                print("⚠️ 请求数不足，跳过API调用测试")
                print("建议等待15分钟后重试")
                return
                
            print("🔍 执行单次用户查询测试...")
            
            # 只进行一次最简单的API调用
            user = await client.get_user_by_username("jack")  # 推特创始人，肯定存在
            
            if user:
                print("✅ API调用成功！")
                print(f"   用户: {user.name}")
                print(f"   用户名: @{user.username}")
                
                # 显示使用情况
                final_rate_limit = client.get_rate_limit_status()
                used_requests = rate_limit['remaining'] - final_rate_limit['remaining']
                print(f"   本次消耗请求数: {used_requests}")
                print(f"   剩余请求数: {final_rate_limit['remaining']}")
                
                return True
            else:
                print("❌ API调用失败")
                return False
                
    except TwitterAPIError as e:
        print(f"❌ API错误: {e.message}")
        return False
    except Exception as e:
        print(f"❌ 未知错误: {str(e)}")
        return False


if __name__ == "__main__":
    result = asyncio.run(lightweight_test())
    
    if result:
        print("\n🎉 推特API基本功能正常")
        print("如需完整测试，请等待速率限制重置")
    else:
        print("\n❌ 推特API测试失败")