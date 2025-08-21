#!/usr/bin/env python3
"""
企业微信通知使用示例
演示各种通知使用场景
"""
import asyncio
import sys
import os
from datetime import datetime

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.services.notification_service import notification_service
from src.services.notification_template_service import template_service, init_default_templates
from src.schemas.notification import (
    NotificationCreate, NotificationTriggerRequest,
    NotificationType, NotificationChannel
)


async def example_basic_notification():
    """示例1: 基础通知发送"""
    print("📤 示例1: 基础通知发送")
    
    notification = NotificationCreate(
        type=NotificationType.SYSTEM,
        title="📋 系统状态更新",
        content="""### 🖥️ 系统运行报告

**服务状态**: 运行正常
**CPU使用率**: 15%
**内存使用率**: 32%
**活跃连接数**: 156

**检查时间**: {current_time}

所有服务运行正常，无需人工干预。""".format(
            current_time=datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        ),
        is_urgent=False,
        channel=NotificationChannel.WECHAT,
        data={"cpu_usage": 15, "memory_usage": 32, "connections": 156}
    )
    
    result = await notification_service.send_notification(notification)
    print(f"发送结果: {'✅ 成功' if result else '❌ 失败'}")
    return result


async def example_urgent_notification():
    """示例2: 紧急通知"""
    print("🚨 示例2: 紧急通知")
    
    notification = NotificationCreate(
        type=NotificationType.SYSTEM,
        title="🚨 系统异常警报",
        content="""### ⚠️ 系统异常检测

**异常类型**: 数据库连接超时
**影响范围**: 用户认证服务
**开始时间**: {current_time}

**错误详情**: 
数据库连接池已满，新连接无法建立

**建议操作**:
1. 检查数据库服务状态
2. 重启数据库连接池
3. 监控后续状态

请立即处理！""".format(
            current_time=datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        ),
        is_urgent=True,  # 紧急通知
        channel=NotificationChannel.WECHAT,
        data={"error_type": "database_timeout", "affected_service": "auth"}
    )
    
    result = await notification_service.send_notification(notification)
    print(f"发送结果: {'✅ 成功' if result else '❌ 失败'}")
    return result


async def example_twitter_notification():
    """示例3: Twitter CA推文通知"""
    print("🐦 示例3: Twitter CA推文通知")
    
    notification = NotificationCreate(
        type=NotificationType.TWITTER,
        title="🚨 CA地址推文提醒",
        content="""### 📱 用户: @crypto_whale
**推文内容**: 🔥 New gem alert! Don't miss this one! 

**CA地址**: `0xabcd1234567890abcdef1234567890abcdef1234`

**推文链接**: https://twitter.com/crypto_whale/status/1234567890

**发布时间**: {tweet_time}

**分析结果**:
- 置信度: 92%
- 风险评分: 4/10
- 用户影响力: 高

⚡ 建议及时关注此推文的后续反应""".format(
            tweet_time=datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        ),
        is_urgent=True,
        channel=NotificationChannel.WECHAT,
        data={
            "username": "crypto_whale",
            "ca_address": "0xabcd1234567890abcdef1234567890abcdef1234",
            "confidence": 92,
            "risk_score": 4
        }
    )
    
    result = await notification_service.send_notification(notification)
    print(f"发送结果: {'✅ 成功' if result else '❌ 失败'}")
    return result


async def example_solana_transaction():
    """示例4: Solana大额交易通知"""
    print("💰 示例4: Solana大额交易通知")
    
    notification = NotificationCreate(
        type=NotificationType.SOLANA,
        title="💰 大额交易检测",
        content="""### 💎 钱包: 鲸鱼钱包A
**交易类型**: DEX交换
**交易对**: USDC → SOL
**交易金额**: 500,000 USDC
**USD价值**: $500,000.00

**交易详情**:
- 输入: 500,000 USDC
- 输出: 4,347 SOL
- 汇率: 1 SOL = $115.02

**交易信息**:
- 签名: `5J9KW...x7mP9`
- DEX: Raydium
- 手续费: 0.025 SOL
- 区块: 234,567,890

**浏览器链接**: https://solscan.io/tx/5J9KW...x7mP9

**时间**: {tx_time}

💡 大额交易可能影响市场价格""".format(
            tx_time=datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        ),
        is_urgent=True,
        channel=NotificationChannel.WECHAT,
        data={
            "wallet": "whale_wallet_a",
            "tx_type": "swap",
            "amount_usd": 500000.00,
            "token_in": "USDC",
            "token_out": "SOL"
        }
    )
    
    result = await notification_service.send_notification(notification)
    print(f"发送结果: {'✅ 成功' if result else '❌ 失败'}")
    return result


async def example_template_notification():
    """示例5: 使用模板发送通知"""
    print("📋 示例5: 使用模板发送通知")
    
    # 确保默认模板存在
    try:
        init_default_templates()
    except Exception:
        pass  # 模板可能已存在
    
    # 使用系统状态模板
    template_request = NotificationTriggerRequest(
        template_name="system_status_alert",
        variables={
            "component": "Solana监控服务",
            "status": "服务重启",
            "message": "由于内存使用率过高，系统自动重启了Solana监控服务。重启后服务运行正常，所有监控钱包已重新连接。",
            "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
    )
    
    result = await notification_service.send_by_template(template_request)
    print(f"发送结果: {'✅ 成功' if result else '❌ 失败'}")
    return result


async def example_custom_template_notification():
    """示例6: 自定义模板通知"""
    print("🎨 示例6: 自定义模板通知")
    
    # 首先创建一个自定义模板
    from src.schemas.notification import NotificationTemplateCreate
    
    custom_template = NotificationTemplateCreate(
        name="daily_report_template",
        type=NotificationType.SYSTEM,
        title_template="📊 {report_date} 日报",
        content_template="""### 📈 每日监控报告

**报告日期**: {report_date}
**监控用户数**: {twitter_users}
**监控钱包数**: {solana_wallets}

**今日活动**:
- 发现CA推文: {ca_tweets} 条
- 重要交易: {important_transactions} 笔
- 发送通知: {notifications_sent} 条

**系统状态**:
- 运行时间: {uptime}
- 成功率: {success_rate}%
- 响应时间: {response_time}ms

**明日计划**:
{tomorrow_plans}

---
*自动生成的日报 - 监控机器人v2.0*""",
        is_active=True,
        is_urgent=False,
        channel=NotificationChannel.WECHAT,
        variables={
            "report_date": "报告日期",
            "twitter_users": "Twitter用户数量",
            "solana_wallets": "Solana钱包数量",
            "ca_tweets": "CA推文数量",
            "important_transactions": "重要交易数量",
            "notifications_sent": "发送通知数量",
            "uptime": "系统运行时间",
            "success_rate": "成功率",
            "response_time": "响应时间",
            "tomorrow_plans": "明日计划"
        }
    )
    
    try:
        template = template_service.create_template(custom_template)
        print(f"✅ 自定义模板创建成功: {template.name}")
    except Exception as e:
        print(f"⚠️ 模板创建警告: {e} (可能已存在)")
    
    # 使用自定义模板发送通知
    template_request = NotificationTriggerRequest(
        template_name="daily_report_template",
        variables={
            "report_date": datetime.now().strftime('%Y-%m-%d'),
            "twitter_users": 15,
            "solana_wallets": 8,
            "ca_tweets": 23,
            "important_transactions": 7,
            "notifications_sent": 45,
            "uptime": "23小时42分钟",
            "success_rate": 98.5,
            "response_time": 127,
            "tomorrow_plans": "- 新增3个Twitter用户监控\n- 优化Solana交易分析算法\n- 更新通知模板"
        }
    )
    
    result = await notification_service.send_by_template(template_request)
    print(f"发送结果: {'✅ 成功' if result else '❌ 失败'}")
    return result


async def example_dedup_notification():
    """示例7: 去重功能演示"""
    print("🔄 示例7: 去重功能演示")
    
    # 使用相同的去重键发送两条通知
    dedup_key = f"demo_dedup_{int(datetime.now().timestamp())}"
    
    # 第一条通知
    notification1 = NotificationCreate(
        type=NotificationType.SYSTEM,
        title="🔄 去重测试 - 第1条",
        content=f"""### 去重功能测试

这是第一条通知，应该正常发送。

**去重键**: {dedup_key}
**发送时间**: {datetime.now().strftime('%H:%M:%S')}""",
        channel=NotificationChannel.WECHAT,
        dedup_key=dedup_key
    )
    
    # 第二条通知（相同去重键）
    notification2 = NotificationCreate(
        type=NotificationType.SYSTEM,
        title="🔄 去重测试 - 第2条",
        content=f"""### 去重功能测试

这是第二条通知，应该被去重过滤。

**去重键**: {dedup_key}
**发送时间**: {datetime.now().strftime('%H:%M:%S')}""",
        channel=NotificationChannel.WECHAT,
        dedup_key=dedup_key
    )
    
    print("发送第一条通知...")
    result1 = await notification_service.send_notification(notification1)
    print(f"第一条结果: {'✅ 成功' if result1 else '❌ 失败'}")
    
    # 等待1秒
    await asyncio.sleep(1)
    
    print("发送第二条通知（应该被去重）...")
    result2 = await notification_service.send_notification(notification2)
    print(f"第二条结果: {'✅ 成功(已去重)' if result2 else '❌ 失败'}")
    
    return result1 and result2


async def example_batch_notifications():
    """示例8: 批量通知发送"""
    print("📦 示例8: 批量通知发送")
    
    # 创建多个不同类型的通知
    notifications = [
        NotificationCreate(
            type=NotificationType.SYSTEM,
            title=f"📊 批量通知 {i+1}",
            content=f"""### 批量测试通知 #{i+1}

这是批量发送测试中的第 {i+1} 条通知。

**批次ID**: batch_001
**序号**: {i+1}/5
**时间**: {datetime.now().strftime('%H:%M:%S')}""",
            channel=NotificationChannel.WECHAT,
            data={"batch_id": "batch_001", "sequence": i+1}
        )
        for i in range(5)
    ]
    
    print("开始批量发送通知...")
    
    # 并发发送所有通知
    tasks = [notification_service.send_notification(notif) for notif in notifications]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # 统计结果
    success_count = sum(1 for r in results if r is True)
    print(f"批量发送完成: {success_count}/{len(notifications)} 条成功")
    
    return success_count == len(notifications)


async def main():
    """主函数 - 运行所有示例"""
    print("🚀 企业微信通知功能示例")
    print("=" * 50)
    
    # 检查配置
    webhook_url = os.getenv("WECHAT_WEBHOOK_URL")
    if not webhook_url:
        print("❌ 未配置 WECHAT_WEBHOOK_URL 环境变量")
        print("请在 .env 文件中添加企业微信 Webhook URL")
        return
    
    print(f"✅ 企业微信配置已就绪")
    print()
    
    # 示例列表
    examples = [
        ("基础通知", example_basic_notification),
        ("紧急通知", example_urgent_notification),
        ("Twitter通知", example_twitter_notification),
        ("Solana交易通知", example_solana_transaction),
        ("模板通知", example_template_notification),
        ("自定义模板", example_custom_template_notification),
        ("去重功能", example_dedup_notification),
        ("批量发送", example_batch_notifications),
    ]
    
    results = []
    
    for name, example_func in examples:
        print(f"\n🎯 运行示例: {name}")
        print("-" * 40)
        
        try:
            result = await example_func()
            results.append((name, result))
            print(f"示例 '{name}': {'✅ 完成' if result else '❌ 失败'}")
        except Exception as e:
            print(f"示例 '{name}': ❌ 异常 - {e}")
            results.append((name, False))
        
        # 避免发送过快
        await asyncio.sleep(2)
    
    # 获取统计信息
    print(f"\n📊 获取通知统计...")
    try:
        stats = await notification_service.get_notification_stats()
        print(f"总通知数: {stats.get('total_notifications', 0)}")
        print(f"成功发送: {stats.get('sent_notifications', 0)}")
        print(f"成功率: {stats.get('success_rate', 0):.1f}%")
    except Exception as e:
        print(f"⚠️ 获取统计失败: {e}")
    
    # 总结
    print("\n" + "=" * 50)
    print("📋 示例运行总结")
    print("=" * 50)
    
    success_count = sum(1 for _, result in results if result)
    total_count = len(results)
    
    for name, result in results:
        status = "✅ 成功" if result else "❌ 失败"
        print(f"  {name}: {status}")
    
    print(f"\n总计: {success_count}/{total_count} 个示例成功")
    
    if success_count == total_count:
        print("🎉 所有示例都运行成功！企业微信通知功能完全正常！")
        print("\n💡 提示: 请检查您的企业微信群，应该收到了多条不同类型的通知消息")
    else:
        print("⚠️ 部分示例失败，请检查配置和网络连接")


if __name__ == "__main__":
    # 加载环境变量
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        print("⚠️ 未安装 python-dotenv，请确保环境变量已正确设置")
    
    # 运行示例
    asyncio.run(main())