#!/usr/bin/env python3
"""
推特API性能测试
分析API调用的具体耗时
"""

import asyncio
import time
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from src.services.twitter_client import TwitterClient, TwitterAPIError


async def measure_api_performance():
    """测量API性能"""
    print("⏱️ 推特API性能测试")
    print("=" * 40)
    
    token = os.getenv('TWITTER_BEARER_TOKEN')
    if not token:
        print("❌ 未找到 TWITTER_BEARER_TOKEN 环境变量")
        return
        
    total_start = time.time()
    
    try:
        # 测试1: 客户端初始化时间
        init_start = time.time()
        async with TwitterClient(token) as client:
            init_end = time.time()
            print(f"🔧 客户端初始化: {(init_end - init_start)*1000:.0f}ms")
            
            # 测试2: 单次用户查询
            print("\n📊 用户查询性能测试:")
            users_to_test = ["elonmusk", "jack", "sundarpichai"]
            
            for username in users_to_test:
                request_start = time.time()
                
                try:
                    user = await client.get_user_by_username(username)
                    request_end = time.time()
                    
                    if user:
                        print(f"✅ @{username}: {(request_end - request_start)*1000:.0f}ms")
                        
                        # 显示速率限制信息
                        rate_limit = client.get_rate_limit_status()
                        print(f"   剩余: {rate_limit['remaining']}")
                    else:
                        print(f"❌ @{username}: 用户不存在")
                        
                except TwitterAPIError as e:
                    request_end = time.time()
                    print(f"❌ @{username}: {(request_end - request_start)*1000:.0f}ms (错误: {e.message})")
                    
                # 短暂延迟避免过快请求
                await asyncio.sleep(0.5)
                
            # 测试3: 推文获取性能
            print(f"\n📱 推文获取性能测试:")
            tweets_start = time.time()
            
            try:
                # 先获取用户ID
                user = await client.get_user_by_username("elonmusk")
                if user:
                    tweets = await client.get_user_tweets(user.id, max_results=5)
                    tweets_end = time.time()
                    
                    print(f"✅ 获取5条推文: {(tweets_end - tweets_start)*1000:.0f}ms")
                    print(f"   推文数量: {len(tweets)}")
                    
                    # 显示最终速率限制状态
                    final_rate_limit = client.get_rate_limit_status()
                    print(f"   最终剩余: {final_rate_limit['remaining']}")
                    
            except TwitterAPIError as e:
                tweets_end = time.time()
                print(f"❌ 推文获取失败: {(tweets_end - tweets_start)*1000:.0f}ms")
                print(f"   错误: {e.message}")
                
        total_end = time.time()
        
        print(f"\n📋 总体性能:")
        print(f"   总耗时: {(total_end - total_start)*1000:.0f}ms ({total_end - total_start:.1f}s)")
        
        # 性能评估
        total_time = total_end - total_start
        if total_time < 5:
            print(f"✅ 性能良好")
        elif total_time < 10:
            print(f"⚠️ 性能一般")
        else:
            print(f"🔴 性能较差，可能是网络问题")
            
        # 给出建议
        print(f"\n💡 性能优化建议:")
        if total_time > 8:
            print(f"   - 检查网络连接速度")
            print(f"   - 考虑使用代理服务器")
            print(f"   - 减少并发请求数量")
        else:
            print(f"   - API响应正常")
            print(f"   - 可以考虑批量处理以提高效率")
            
    except Exception as e:
        print(f"❌ 性能测试失败: {str(e)}")


async def simple_speed_test():
    """简单的速度测试"""
    print("🚀 快速速度测试")
    print("-" * 20)
    
    token = os.getenv('TWITTER_BEARER_TOKEN')
    if not token:
        print("❌ 未找到 TWITTER_BEARER_TOKEN")
        return
        
    start_time = time.time()
    
    async with TwitterClient(token) as client:
        user = await client.get_user_by_username("jack")
        
    end_time = time.time()
    
    if user:
        elapsed_ms = (end_time - start_time) * 1000
        print(f"✅ 单次用户查询: {elapsed_ms:.0f}ms")
        
        if elapsed_ms < 1000:
            print("🟢 速度很快")
        elif elapsed_ms < 3000:
            print("🟡 速度正常") 
        else:
            print("🔴 速度较慢")
    else:
        print("❌ 查询失败")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser()
    parser.add_argument("--simple", action="store_true", help="运行简单测试")
    args = parser.parse_args()
    
    if args.simple:
        asyncio.run(simple_speed_test())
    else:
        asyncio.run(measure_api_performance())