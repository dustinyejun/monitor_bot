#!/usr/bin/env python3
"""
企业微信通知真实测试脚本
用于测试企业微信通知功能是否正常工作
"""
import asyncio
import os
from datetime import datetime
from src.services.notification_service import notification_service
# 移除模板服务依赖 - 现在使用硬编码配置
from src.schemas.notification import NotificationCreate, NotificationTriggerRequest
from src.schemas.notification import NotificationType, NotificationChannel


async def test_twitter_notification():
    """测试Twitter通知发送"""
    print("🐦 测试Twitter通知发送...")
    
    notification = NotificationCreate(
        type=NotificationType.TWITTER,
        title="🔍 Twitter监控测试",
        content=f"""### 🐦 Twitter监控功能测试

**测试时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**测试用户**: @test_user
**模拟CA地址**: 0x1234567890abcdef1234567890abcdef12345678

这是Twitter CA地址监控功能的测试通知。

如果收到此消息，说明Twitter监控通知正常！ ✅

---
*Twitter监控插件 - 智能CA识别*""",
        is_urgent=False,
        channel=NotificationChannel.WECHAT,
        data={"test": True, "test_type": "twitter_basic"}
    )
    
    try:
        result = await notification_service.send_notification(notification)
        if result:
            print("✅ Twitter通知发送成功！")
        else:
            print("❌ Twitter通知发送失败！")
        return result
    except Exception as e:
        print(f"❌ Twitter通知发送异常: {e}")
        return False


async def test_urgent_notification():
    """测试紧急通知发送"""
    print("🚨 测试紧急通知发送...")
    
    notification = NotificationCreate(
        type=NotificationType.TWITTER,
        title="🚨 CA地址推文提醒",
        content=f"""### 📱 用户: test_user
**推文内容**: 🔥 New gem found! CA: 0x1234567890abcdef

**CA地址**: `0x1234567890abcdef1234567890abcdef12345678`

**推文链接**: https://twitter.com/test_user/status/123456789

**发布时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

**置信度**: 95%
**风险评分**: 3/10

---
⚡ 这是一条紧急通知测试""",
        is_urgent=True,
        channel=NotificationChannel.WECHAT,
        data={"test": True, "test_type": "urgent", "ca_address": "0x1234567890abcdef"}
    )
    
    try:
        result = await notification_service.send_notification(notification)
        if result:
            print("✅ 紧急通知发送成功！")
        else:
            print("❌ 紧急通知发送失败！")
        return result
    except Exception as e:
        print(f"❌ 紧急通知发送异常: {e}")
        return False


async def test_twitter_template_notification():
    """测试Twitter模板通知发送"""
    print("📋 测试Twitter模板通知发送...")
    
    # 模板现在硬编码在 src/config/notification_config.py 中，无需初始化
    
    template_request = NotificationTriggerRequest(
        template_name="twitter_ca_alert",
        variables={
            "username": "crypto_influencer",
            "content": "🔥 New gem found! CA: 0x1234567890abcdef1234567890abcdef12345678",
            "ca_addresses": "0x1234567890abcdef1234567890abcdef12345678",
            "tweet_url": "https://twitter.com/crypto_influencer/status/123456789",
            "tweet_created_at": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
    )
    
    try:
        result = await notification_service.send_by_template(template_request)
        if result:
            print("✅ Twitter模板通知发送成功！")
        else:
            print("❌ Twitter模板通知发送失败！")
        return result
    except Exception as e:
        print(f"❌ Twitter模板通知发送异常: {e}")
        return False


async def test_solana_notification():
    """测试Solana大额交易通知"""
    print("💰 测试Solana交易通知发送...")
    
    # 模板现在硬编码配置，无需初始化
    
    template_request = NotificationTriggerRequest(
        template_name="solana_transaction",
        variables={
            "wallet_alias": "聪明钱钱包A",
            "transaction_type": "swap", 
            "amount": "1000000",
            "token_symbol": "PEPE",
            "amount_usd": 1000000.00,
            "token_name": "Pepe Token",
            "token_address": "6GCLMHHaMKbKHPsLLSzFGg5RnHJMd9GX3RRVX7hHNAjf",  # CA地址
            "purchase_count": "3",  # 第3笔购买该代币
            "total_token_amount": "15000000000",  # 总购买了150亿PEPE
            "total_invested_usd": 2500000.00,  # 总投资250万USD
            "avg_purchase_usd": 833333.33,  # 平均83万USD每笔
            "signature": "5J7XKVxF9B3R2mK8pQ1nN7yT4cW6sD2eF8hG9xA3mP5vQ7rS4tU1",
            "solscan_url": f"https://solscan.io/tx/5J7XKVxF9B3R2mK8pQ1nN7yT4cW6sD2eF8hG9xA3mP5vQ7rS4tU1",
            "block_time": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
    )
    
    try:
        result = await notification_service.send_by_template(template_request)
        if result:
            print("✅ Solana交易通知发送成功！")
        else:
            print("❌ Solana交易通知发送失败！")
        return result
    except Exception as e:
        print(f"❌ Solana交易通知发送异常: {e}")
        return False


async def test_duplicate_notification():
    """测试去重功能"""
    print("🔄 测试通知去重功能...")
    
    # 发送两条相同去重键的Twitter通知
    dedup_key = f"test_dedup_{int(datetime.now().timestamp())}"
    
    notification1 = NotificationCreate(
        type=NotificationType.TWITTER,
        title="去重测试通知 1",
        content="🐦 第一条Twitter去重测试通知\n**CA地址**: 0x1234567890abcdef1234567890abcdef12345678",
        channel=NotificationChannel.WECHAT,
        dedup_key=dedup_key,
        data={"test": True, "sequence": 1, "ca_address": "0x1234567890abcdef1234567890abcdef12345678"}
    )
    
    notification2 = NotificationCreate(
        type=NotificationType.TWITTER,
        title="去重测试通知 2", 
        content="🐦 第二条Twitter去重测试通知（应该被去重）\n**CA地址**: 0x1234567890abcdef1234567890abcdef12345678",
        channel=NotificationChannel.WECHAT,
        dedup_key=dedup_key,
        data={"test": True, "sequence": 2, "ca_address": "0x1234567890abcdef1234567890abcdef12345678"}
    )
    
    try:
        # 发送第一条
        result1 = await notification_service.send_notification(notification1)
        print(f"第一条通知结果: {'✅ 成功' if result1 else '❌ 失败'}")
        
        # 等待1秒后发送第二条
        await asyncio.sleep(1)
        result2 = await notification_service.send_notification(notification2)
        print(f"第二条通知结果: {'✅ 成功(已去重)' if result2 else '❌ 失败'}")
        
        return result1 and result2
        
    except Exception as e:
        print(f"❌ 去重测试异常: {e}")
        return False


async def get_notification_stats():
    """获取通知统计"""
    print("📊 获取通知统计信息...")
    
    try:
        stats = await notification_service.get_notification_stats()
        
        print("📈 通知统计:")
        print(f"  总通知数: {stats.get('total_notifications', 0)}")
        print(f"  已发送: {stats.get('sent_notifications', 0)}")
        print(f"  发送失败: {stats.get('failed_notifications', 0)}")
        print(f"  待发送: {stats.get('pending_notifications', 0)}")
        print(f"  紧急通知: {stats.get('urgent_notifications', 0)}")
        print(f"  今日通知: {stats.get('today_notifications', 0)}")
        print(f"  成功率: {stats.get('success_rate', 0):.2f}%")
        
        if stats.get('type_stats'):
            print("  按类型统计:")
            for type_name, count in stats['type_stats'].items():
                print(f"    {type_name}: {count}")
        
        return True
        
    except Exception as e:
        print(f"❌ 获取统计失败: {e}")
        return False


async def main():
    """主测试函数"""
    print("🚀 开始企业微信通知功能测试")
    print("=" * 50)
    
    # 检查配置
    webhook_url = os.getenv("WECHAT_WEBHOOK_URL")
    if not webhook_url:
        print("❌ 错误: 未设置 WECHAT_WEBHOOK_URL 环境变量")
        print("请在 .env 文件中配置企业微信 Webhook URL")
        return
    
    print(f"✅ 企业微信 Webhook URL 已配置: {webhook_url[:50]}...")
    print()
    
    # 运行测试 - 只保留核心监控通知
    tests = [
        ("Twitter基础通知", test_twitter_notification),
        ("Twitter紧急通知", test_urgent_notification), 
        ("Twitter模板通知", test_twitter_template_notification),
        ("Solana交易通知", test_solana_notification),
        ("去重功能测试", test_duplicate_notification),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        print(f"🧪 运行测试: {test_name}")
        try:
            result = await test_func()
            results.append((test_name, result))
            print(f"{'✅ 通过' if result else '❌ 失败'}: {test_name}")
        except Exception as e:
            print(f"❌ 异常: {test_name} - {e}")
            results.append((test_name, False))
        
        print("-" * 30)
        await asyncio.sleep(1)  # 避免发送过快
    
    # 获取统计信息
    await get_notification_stats()
    
    # 总结结果
    print("📋 测试总结:")
    print("=" * 50)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"  {test_name}: {status}")
    
    print()
    print(f"总计: {passed}/{total} 个测试通过")
    
    if passed == total:
        print("🎉 所有测试通过！企业微信通知功能正常！")
    else:
        print("⚠️ 部分测试失败，请检查配置和网络连接")


if __name__ == "__main__":
    # 加载环境变量
    try:
        from dotenv import load_dotenv
        load_dotenv()
        print("✅ 环境变量加载完成")
    except ImportError:
        print("⚠️ 未安装 python-dotenv")
    
    # 设置事件循环策略（Mac上可能需要）
    if hasattr(asyncio, 'set_event_loop_policy'):
        try:
            asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
        except AttributeError:
            pass
    
    # 运行测试
    asyncio.run(main())