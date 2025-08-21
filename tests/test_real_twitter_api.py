"""
真实推特API测试脚本
用于测试与推特API的实际连接和功能
"""

import asyncio
import os
from pathlib import Path
import sys

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.services.twitter_client import TwitterClient, TwitterAPIError
from src.services.twitter_analyzer import TwitterAnalyzer
from src.utils.logger import logger


class RealTwitterAPITest:
    """真实推特API测试类"""
    
    def __init__(self):
        self.bearer_token = os.getenv('TWITTER_BEARER_TOKEN')
        self.analyzer = TwitterAnalyzer()
        
        if not self.bearer_token:
            raise ValueError("请设置 TWITTER_BEARER_TOKEN 环境变量")
            
    async def test_api_connection(self):
        """测试API连接"""
        print("🔧 测试1: API连接...")
        
        try:
            async with TwitterClient(self.bearer_token) as client:
                # 获取速率限制状态
                rate_limit = client.get_rate_limit_status()
                print(f"✅ API连接成功")
                print(f"   剩余请求数: {rate_limit['remaining']}")
                if rate_limit['reset_datetime']:
                    print(f"   重置时间: {rate_limit['reset_datetime']}")
                return True
        except Exception as e:
            print(f"❌ API连接失败: {str(e)}")
            return False
            
    async def test_get_user_info(self, username: str = "elonmusk"):
        """测试获取用户信息"""
        print(f"\n🔧 测试2: 获取用户信息 (@{username})...")
        
        try:
            async with TwitterClient(self.bearer_token) as client:
                user_info = await client.get_user_by_username(username)
                
                if user_info:
                    print(f"✅ 用户信息获取成功:")
                    print(f"   用户ID: {user_info.id}")
                    print(f"   用户名: @{user_info.username}")
                    print(f"   显示名: {user_info.name}")
                    print(f"   粉丝数: {user_info.public_metrics.get('followers_count', 'N/A')}")
                    print(f"   关注数: {user_info.public_metrics.get('following_count', 'N/A')}")
                    return user_info
                else:
                    print(f"❌ 用户 @{username} 不存在")
                    return None
                    
        except TwitterAPIError as e:
            print(f"❌ 获取用户信息失败: {e.message}")
            if e.status_code:
                print(f"   状态码: {e.status_code}")
            return None
        except Exception as e:
            print(f"❌ 未知错误: {str(e)}")
            return None
            
    async def test_get_user_tweets(self, username: str = "elonmusk", max_results: int = 5):
        """测试获取用户推文"""
        print(f"\n🔧 测试3: 获取用户推文 (@{username}, 最近{max_results}条)...")
        
        try:
            async with TwitterClient(self.bearer_token) as client:
                # 先获取用户ID
                # user_info = await client.get_user_by_username(username)
                # if not user_info:
                #     print(f"❌ 无法获取用户 @{username} 的信息")
                #     return []
                    
                # 获取推文
                tweets = await client.get_user_tweets(
                    user_id='44196397',
                    max_results=max_results
                )
                
                if tweets:
                    print(f"✅ 成功获取 {len(tweets)} 条推文:")
                    for i, tweet in enumerate(tweets[:3], 1):  # 显示前3条
                        print(f"\n   推文 {i}:")
                        print(f"   ID: {tweet.id}")
                        print(f"   时间: {tweet.created_at}")
                        print(f"   内容: {tweet.text[:100]}...")
                        print(f"   点赞: {tweet.public_metrics.get('like_count', 0)}")
                        print(f"   转发: {tweet.public_metrics.get('retweet_count', 0)}")
                    
                    if len(tweets) > 3:
                        print(f"   (还有 {len(tweets) - 3} 条推文未显示)")
                        
                    return tweets
                else:
                    print("❌ 未获取到推文")
                    return []
                    
        except TwitterAPIError as e:
            print(f"❌ 获取推文失败: {e.message}")
            if e.status_code:
                print(f"   状态码: {e.status_code}")
            return []
        except Exception as e:
            print(f"❌ 未知错误: {str(e)}")
            return []
            
    async def test_ca_analysis(self, username: str = "elonmusk"):
        """测试CA地址分析"""
        print(f"\n🔧 测试4: CA地址分析...")
        
        try:
            # 获取推文
            tweets = await self.test_get_user_tweets(username, max_results=10)
            if not tweets:
                print("❌ 无法获取推文进行分析")
                return
                
            ca_found = 0
            print(f"\n🔍 分析 {len(tweets)} 条推文中的CA地址:")
            
            for tweet in tweets:
                analysis_result = self.analyzer.analyze_tweet(tweet.text)
                
                if analysis_result.has_ca:
                    ca_found += 1
                    print(f"\n✅ 发现CA地址 (推文ID: {tweet.id}):")
                    print(f"   推文内容: {tweet.text[:100]}...")
                    print(f"   CA地址数量: {len(analysis_result.ca_addresses)}")
                    
                    for addr in analysis_result.ca_addresses:
                        print(f"     - 地址: {addr.address}")
                        print(f"       类型: {addr.type.value}")
                        print(f"       置信度: {addr.confidence:.2f}")
                        
                    if analysis_result.keywords_found:
                        print(f"   关键词: {', '.join(analysis_result.keywords_found)}")
                    print(f"   风险评分: {analysis_result.risk_score:.2f}")
                    
            print(f"\n📊 分析结果: {len(tweets)} 条推文中发现 {ca_found} 条包含CA地址")
            
        except Exception as e:
            print(f"❌ CA分析失败: {str(e)}")
            
    async def test_rate_limit_handling(self):
        """测试速率限制处理"""
        print(f"\n🔧 测试5: 速率限制处理...")
        
        try:
            async with TwitterClient(self.bearer_token) as client:
                print("   发送多个连续请求测试速率限制...")
                
                # 连续发送几个请求
                usernames = ["elonmusk", "jack", "sundarpichai"]
                
                for username in usernames:
                    try:
                        user_info = await client.get_user_by_username(username)
                        if user_info:
                            print(f"   ✅ @{username}: {user_info.name}")
                        else:
                            print(f"   ❌ @{username}: 用户不存在")
                            
                        # 检查速率限制状态
                        rate_limit = client.get_rate_limit_status()
                        print(f"      剩余请求: {rate_limit['remaining']}")
                        
                    except TwitterAPIError as e:
                        if e.status_code == 429:
                            print(f"   ⚠️ 遇到速率限制: {e.message}")
                        else:
                            print(f"   ❌ API错误: {e.message}")
                            
                print("✅ 速率限制处理测试完成")
                
        except Exception as e:
            print(f"❌ 速率限制测试失败: {str(e)}")
            
    async def run_all_tests(self):
        """运行所有测试"""
        print("🚀 开始推特API完整测试...\n")
        print("=" * 50)
        
        # # 测试1: API连接
        # connection_ok = await self.test_api_connection()
        # if not connection_ok:
        #     print("\n❌ API连接失败，停止后续测试")
        #     return
            
        # # 测试2: 获取用户信息
        # await self.test_get_user_info()
        
        # 测试3: 获取推文
        await self.test_get_user_tweets()
        
        # 测试4: CA地址分析
        await self.test_ca_analysis()
        
        # 测试5: 速率限制
        await self.test_rate_limit_handling()
        
        print("\n" + "=" * 50)
        print("🎉 推特API测试完成!")


async def main():
    """主函数"""
    try:
        tester = RealTwitterAPITest()
        await tester.run_all_tests()
    except ValueError as e:
        print(f"❌ 配置错误: {str(e)}")
        print("\n请按照以下步骤配置:")
        print("1. 获取推特API Bearer Token")
        print("2. 设置环境变量: export TWITTER_BEARER_TOKEN='your_token_here'")
        print("3. 重新运行测试")
    except Exception as e:
        print(f"❌ 测试失败: {str(e)}")


if __name__ == "__main__":
    asyncio.run(main())