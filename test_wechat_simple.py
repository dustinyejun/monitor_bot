#!/usr/bin/env python3
"""
企业微信通知简单测试（无需数据库）
直接调用企业微信API，不依赖数据库
"""
import asyncio
import os
import sys
import aiohttp
from datetime import datetime

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


async def send_wechat_message(webhook_url: str, title: str, content: str, is_urgent: bool = False):
    """直接发送企业微信消息，不依赖数据库"""
    try:
        # 构造消息内容
        if is_urgent:
            formatted_content = f"## 🚨 {title}\n\n{content}\n\n⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        else:
            formatted_content = f"## {title}\n\n{content}\n\n⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        
        # 企业微信消息格式
        message = {
            "msgtype": "markdown",
            "markdown": {
                "content": formatted_content
            }
        }
        
        # 发送HTTP请求
        timeout = aiohttp.ClientTimeout(total=10)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.post(webhook_url, json=message) as response:
                if response.status == 200:
                    result = await response.json()
                    if result.get("errcode") == 0:
                        print("✅ 企业微信消息发送成功！")
                        return True
                    else:
                        print(f"❌ 企业微信API错误: {result}")
                        return False
                else:
                    print(f"❌ HTTP请求失败: {response.status}")
                    return False
    
    except asyncio.TimeoutError:
        print("❌ 网络请求超时")
        return False
    except Exception as e:
        print(f"❌ 发送消息异常: {e}")
        return False


async def test_basic_notification(webhook_url: str):
    """测试基础通知"""
    print("📤 测试基础通知...")
    
    title = "🧪 系统测试通知"
    content = f"""### 📋 企业微信通知测试

**测试时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**测试类型**: 无数据库依赖测试

这是一条测试通知，用于验证企业微信通知功能。

**测试状态**: 正常
**网络连接**: 正常
**消息格式**: Markdown

如果您收到这条消息，说明企业微信通知功能工作正常！ ✅"""
    
    return await send_wechat_message(webhook_url, title, content, False)


async def test_urgent_notification(webhook_url: str):
    """测试紧急通知"""
    print("🚨 测试紧急通知...")
    
    title = "🚨 紧急通知测试"
    content = f"""### ⚠️ 紧急通知格式测试

**警报类型**: 测试警报
**触发时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

这是紧急通知格式的测试消息。

**特点**:
- 标题带有🚨标识
- 格式更加醒目
- 用于重要事件通知

**测试完成**: 紧急通知格式正常 ✅"""
    
    return await send_wechat_message(webhook_url, title, content, True)


async def test_twitter_style_notification(webhook_url: str):
    """测试Twitter风格通知"""
    print("🐦 测试Twitter风格通知...")
    
    title = "🚨 CA地址推文提醒"
    content = f"""### 📱 用户: @test_user
**推文内容**: 🔥 发现新的gem代币！CA地址如下

**CA地址**: `0x1234567890abcdef1234567890abcdef12345678`

**推文链接**: https://twitter.com/test_user/status/123456789

**发布时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

**分析结果**:
- 置信度: 95%
- 风险评分: 3/10
- 用户影响力: 高

⚡ 这是模拟的Twitter CA地址推文通知"""
    
    return await send_wechat_message(webhook_url, title, content, True)


async def test_solana_style_notification(webhook_url: str):
    """测试Solana风格通知"""
    print("💰 测试Solana风格通知...")
    
    title = "💰 大额交易提醒"
    content = f"""### 💎 钱包: 测试钱包
**交易类型**: DEX交换
**金额**: 1,000,000 USDC
**USD价值**: $1,000,000.00

**代币**: USD Coin (USDC)
**交易签名**: `5J7XKVxF9B3R2mK8pQ1nN7yT4cW6sD2eF8hG9xA3mP5vQ7rS4tU1`

**浏览器链接**: https://solscan.io/tx/5J7XKVxF9B3R2mK8pQ1nN7yT4cW6sD2eF8hG9xA3mP5vQ7rS4tU1
**交易时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

💡 这是模拟的Solana大额交易通知"""
    
    return await send_wechat_message(webhook_url, title, content, True)


async def main():
    """主测试函数"""
    print("🚀 企业微信通知简单测试（无数据库依赖）")
    print("=" * 60)
    
    # 检查配置
    webhook_url = os.getenv("WECHAT_WEBHOOK_URL")
    if not webhook_url:
        print("❌ 错误: 未设置 WECHAT_WEBHOOK_URL 环境变量")
        print("请在 .env 文件中配置企业微信 Webhook URL")
        return
    
    print(f"✅ 企业微信 Webhook URL 已配置")
    print(f"🔗 URL: {webhook_url[:50]}...")
    print()
    
    # 运行测试
    tests = [
        ("基础通知", test_basic_notification),
        ("紧急通知", test_urgent_notification),
        ("Twitter风格通知", test_twitter_style_notification),
        ("Solana风格通知", test_solana_style_notification),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        print(f"🧪 运行测试: {test_name}")
        try:
            result = await test_func(webhook_url)
            results.append((test_name, result))
            print(f"{'✅ 通过' if result else '❌ 失败'}: {test_name}")
        except Exception as e:
            print(f"❌ 异常: {test_name} - {e}")
            results.append((test_name, False))
        
        print("-" * 40)
        await asyncio.sleep(2)  # 避免发送过快
    
    # 总结结果
    print("📋 测试总结:")
    print("=" * 60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"  {test_name}: {status}")
    
    print()
    print(f"总计: {passed}/{total} 个测试通过")
    
    if passed == total:
        print("🎉 所有测试通过！企业微信通知功能正常！")
        print("💡 提示: 请检查您的企业微信群，应该收到了4条不同风格的测试消息")
    else:
        print("⚠️ 部分测试失败，请检查企业微信配置和网络连接")
    
    print("\n📝 注意: 这是简化版测试，不依赖数据库")
    print("如需完整功能测试，请启动PostgreSQL数据库后运行完整版测试")


if __name__ == "__main__":
    # 加载环境变量
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        print("⚠️ 未安装 python-dotenv，请确保环境变量已正确设置")
    
    # 运行测试
    asyncio.run(main())