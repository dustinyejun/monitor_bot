#!/usr/bin/env python3
"""
检查当前API速率限制状态
"""

import asyncio
import os
import sys
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent))

from src.services.twitter_client import TwitterClient


async def check_rate_limit():
    """检查当前速率限制状态"""
    token = os.getenv('TWITTER_BEARER_TOKEN')
    if not token:
        print("❌ 未找到 TWITTER_BEARER_TOKEN 环境变量")
        return
        
    print("🔍 检查推特API速率限制状态...")
    print("-" * 40)
    
    try:
        async with TwitterClient(token) as client:
            # 获取当前状态（不发送实际请求）
            rate_limit = client.get_rate_limit_status()
            
            print(f"📊 当前状态:")
            print(f"   剩余请求数: {rate_limit['remaining']}")
            print(f"   重置时间戳: {rate_limit['reset_time']}")
            
            if rate_limit['reset_datetime']:
                now = datetime.now()
                reset_time = rate_limit['reset_datetime']
                wait_seconds = (reset_time - now).total_seconds()
                
                print(f"   重置时间: {reset_time.strftime('%H:%M:%S')}")
                print(f"   当前时间: {now.strftime('%H:%M:%S')}")
                
                if wait_seconds > 0:
                    minutes = int(wait_seconds // 60)
                    seconds = int(wait_seconds % 60)
                    print(f"   等待时间: {minutes}分{seconds}秒")
                    print(f"   建议: 等待后再进行测试")
                else:
                    print(f"   ✅ 速率限制已重置，可以正常使用")
            else:
                print(f"   ✅ 首次使用，可以正常请求")
                
            # 给出建议
            if rate_limit['remaining'] > 20:
                print(f"\n💚 状态良好: 可以继续测试")
            elif rate_limit['remaining'] > 5:
                print(f"\n💛 需要注意: 建议减少请求频率")
            else:
                print(f"\n🔴 接近限制: 建议等待重置")
                
    except Exception as e:
        print(f"❌ 检查失败: {str(e)}")


if __name__ == "__main__":
    asyncio.run(check_rate_limit())