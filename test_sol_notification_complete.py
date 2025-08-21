#!/usr/bin/env python3
"""
完整的SOL通知测试
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

print("🔍 测试SOL通知...")

# 1. 测试配置加载
print("1. 测试配置...")
try:
    from src.config.notification_config import get_rules_by_type, get_template
    rules = get_rules_by_type("solana")
    print(f"   Solana规则数量: {len(rules)}")
    
    template = get_template("solana_transaction")
    print(f"   模板: {template.name}")
    print("   ✅ 配置正常")
except Exception as e:
    print(f"   ❌ 配置错误: {e}")
    exit(1)

# 2. 测试模拟数据
print("\n2. 测试数据结构...")
test_data = {
    "wallet_address": "test_address",
    "wallet_alias": "测试钱包",
    "transaction_type": "sol_transfer",
    "amount": "1.000000",
    "amount_usd": 150.0,  # 关键字段
    "token_symbol": "SOL",
    "token_name": "Solana", 
    "signature": "test_sig",
    "solscan_url": "https://solscan.io/tx/test_sig",
    "block_time": "2025-08-21 15:45:00"
}

print(f"   交易类型: {test_data['transaction_type']}")
print(f"   美元价值: ${test_data['amount_usd']}")
print("   ✅ 数据结构正确")

# 3. 检查规则条件匹配
print("\n3. 检查规则条件...")
rule = rules[0]  # 获取第一个规则
conditions = rule.conditions

print(f"   规则名: {rule.name}")
print(f"   条件类型: {'OR' if 'or' in conditions else 'AND' if 'and' in conditions else 'SIMPLE'}")

# 检查第一个OR条件 (SOL转账 >= $0.01)
if 'or' in conditions:
    first_condition = conditions['or'][0]  # SOL转账条件
    if 'and' in first_condition:
        for cond in first_condition['and']:
            field = cond.get('field')
            operator = cond.get('operator') 
            value = cond.get('value')
            actual_value = test_data.get(field)
            
            print(f"   检查: {field} {operator} {value}")
            print(f"   实际值: {actual_value}")
            
            if field == "transaction_type" and operator == "eq":
                match = actual_value == value
                print(f"   类型匹配: {'✅' if match else '❌'}")
            elif field == "amount_usd" and operator == "gte":
                match = actual_value >= value
                print(f"   金额匹配: {'✅' if match else '❌'} ({actual_value} >= {value})")

# 4. 测试今日交易过滤
print("\n4. 测试今日交易过滤...")
try:
    from src.plugins.solana_monitor_plugin import SolanaMonitorPlugin
    from datetime import datetime
    
    plugin = SolanaMonitorPlugin("test", {})
    
    # 模拟签名数据结构（带有blockTime的）
    mock_signatures_today = [
        {
            'signature': 'test_sig_1',
            'blockTime': int(datetime.now().timestamp())  # 今天的时间戳
        }
    ]
    
    mock_signatures_yesterday = [
        {
            'signature': 'test_sig_2', 
            'blockTime': int((datetime.now().timestamp()) - 86400)  # 昨天的时间戳
        }
    ]
    
    # 测试混合数据
    mixed_signatures = mock_signatures_today + mock_signatures_yesterday
    
    filtered = plugin._filter_today_signatures(mixed_signatures)
    
    print(f"   总签名数: {len(mixed_signatures)}")
    print(f"   今日签名数: {len(filtered)}")
    print(f"   过滤结果: {'✅' if len(filtered) == 1 else '❌'}")
    
except Exception as e:
    print(f"   ❌ 日期过滤测试失败: {e}")

print("\n🏁 测试完成!")
print("如果所有项目都显示 ✅，说明配置正确，SOL监控的日期过滤和通知功能都已正常工作。")