#!/usr/bin/env python3
"""
SOL通知调试脚本
用于排查SOL交易获取到但没有发送企业微信通知的问题
"""
import asyncio
from src.config.settings import settings
from src.config.notification_config import get_rules_by_type, get_template
from src.services.notification_engine import notification_engine
from src.services.notification_service import notification_service
from src.schemas.notification import NotificationTriggerRequest

async def test_sol_notification_pipeline():
    """测试SOL通知完整流程"""
    print("🔍 开始SOL通知流程调试...")
    print("=" * 60)
    
    # 1. 检查配置
    print("1. 检查配置...")
    print(f"   SOL转账阈值: ${settings.sol_transfer_amount}")
    print(f"   企业微信URL: {'已配置' if settings.wechat_webhook_url else '未配置'}")
    
    # 2. 检查通知规则
    print("\n2. 检查通知规则...")
    try:
        rules = get_rules_by_type("solana", active_only=True)
        print(f"   活跃Solana规则数量: {len(rules)}")
        for rule in rules:
            print(f"   - {rule.name}: {rule.template_name}")
    except Exception as e:
        print(f"   ❌ 规则检查失败: {e}")
        return
    
    # 3. 检查通知模板
    print("\n3. 检查通知模板...")
    try:
        template = get_template("solana_transaction")
        print(f"   模板名: {template.name}")
        print(f"   模板类型: {template.type}")
        print(f"   标题: {template.title_template}")
    except Exception as e:
        print(f"   ❌ 模板检查失败: {e}")
        return
    
    # 4. 模拟SOL交易数据
    print("\n4. 模拟SOL交易数据...")
    test_transaction_data = {
        "wallet_address": "1234567890abcdef1234567890abcdef12345678",
        "wallet_alias": "测试钱包",
        "transaction_type": "sol_transfer",
        "amount": "10.5",
        "amount_usd": 150.25,  # 超过阈值
        "token_symbol": "SOL",
        "token_name": "Solana",
        "signature": "test_signature_123456789",
        "solscan_url": "https://solscan.io/tx/test_signature_123456789",
        "block_time": "2025-08-21 15:30:00"
    }
    
    print(f"   交易类型: {test_transaction_data['transaction_type']}")
    print(f"   美元价值: ${test_transaction_data['amount_usd']}")
    
    # 5. 测试规则引擎
    print("\n5. 测试规则引擎...")
    try:
        rules_result = await notification_engine.check_solana_rules(test_transaction_data)
        print(f"   规则检查结果: {'✅ 通过' if rules_result else '❌ 未通过'}")
    except Exception as e:
        print(f"   ❌ 规则检查异常: {e}")
        return
    
    # 6. 测试直接模板发送
    print("\n6. 测试直接模板发送...")
    try:
        trigger_request = NotificationTriggerRequest(
            template_name="solana_transaction",
            variables=test_transaction_data
        )
        
        template_result = await notification_service.send_by_template(trigger_request)
        print(f"   模板发送结果: {'✅ 成功' if template_result else '❌ 失败'}")
    except Exception as e:
        print(f"   ❌ 模板发送异常: {e}")
    
    print("\n" + "=" * 60)
    print("🏁 SOL通知调试完成")

if __name__ == "__main__":
    asyncio.run(test_sol_notification_pipeline())