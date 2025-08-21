#!/usr/bin/env python3
"""
调试SOL监控逻辑
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# 手动加载环境变量
try:
    with open('.env', 'r') as f:
        for line in f:
            if line.strip() and not line.startswith('#'):
                key, value = line.strip().split('=', 1)
                os.environ[key] = value
except FileNotFoundError:
    print("⚠️ .env文件未找到")

print("🔍 调试SOL监控逻辑...")

def test_monitoring_flow():
    """测试监控流程的各个环节"""
    
    print("\n1. 测试配置加载...")
    try:
        from src.config.settings import settings
        print(f"   SOL转账阈值: ${settings.sol_transfer_amount}")
        print(f"   DEX交换阈值: ${settings.dex_swap_amount}")
        print(f"   ✅ 配置加载正常")
    except Exception as e:
        print(f"   ❌ 配置加载失败: {e}")
        return

    print("\n2. 测试数据库连接...")
    try:
        from src.services.solana_monitor import SolanaMonitorService
        monitor = SolanaMonitorService()
        wallets = monitor.get_active_wallets()
        print(f"   活跃钱包数量: {len(wallets)}")
        if wallets:
            wallet = wallets[0]
            print(f"   示例钱包: {wallet.address[:8]}...")
            print(f"   最后签名: {wallet.last_signature[:16] if wallet.last_signature else 'None'}...")
        print("   ✅ 数据库连接正常")
    except Exception as e:
        print(f"   ❌ 数据库连接失败: {e}")
        return

    print("\n3. 测试重要性检查逻辑...")
    try:
        # 模拟一个交易分析结果
        from src.services.solana_analyzer import TransactionType
        
        class MockAnalysis:
            def __init__(self):
                self.transaction_type = TransactionType.SOL_TRANSFER
                self.total_value_usd = 0.001  # 很小的值
                self.transfer_info = None
                self.swap_info = None
        
        class MockTransferInfo:
            def __init__(self):
                self.amount = 0.1  # 0.1 SOL
                
        # 测试1: 只有美元价值
        analysis1 = MockAnalysis()
        analysis1.total_value_usd = 0.001  # $0.001
        
        # 测试2: 有转账信息但无美元价值
        analysis2 = MockAnalysis()
        analysis2.total_value_usd = None
        analysis2.transfer_info = MockTransferInfo()
        
        # 测试3: 有美元价值和转账信息
        analysis3 = MockAnalysis()
        analysis3.total_value_usd = 1.0  # $1.0
        analysis3.transfer_info = MockTransferInfo()
        
        print(f"   测试用例1: 美元价值=${analysis1.total_value_usd}")
        print(f"   测试用例2: 转账金额=0.1 SOL, 美元价值=None")
        print(f"   测试用例3: 美元价值=${analysis3.total_value_usd}, 转账金额=0.1 SOL")
        
        print("   ✅ 测试数据准备完成")
        
    except Exception as e:
        print(f"   ❌ 测试准备失败: {e}")
        return

    print("\n4. 检查通知规则...")
    try:
        from src.config.notification_config import get_rules_by_type
        rules = get_rules_by_type("solana")
        if rules:
            rule = rules[0]
            print(f"   规则名: {rule.name}")
            print(f"   模板: {rule.template_name}")
            
            # 检查规则条件
            conditions = rule.conditions
            if 'or' in conditions:
                sol_condition = conditions['or'][0]  # SOL转账条件
                if 'and' in sol_condition:
                    for cond in sol_condition['and']:
                        if cond['field'] == 'amount_usd':
                            print(f"   通知阈值: ${cond['value']}")
        print("   ✅ 通知规则正常")
    except Exception as e:
        print(f"   ❌ 通知规则检查失败: {e}")

    print("\n🎯 可能的问题原因:")
    print("   1. 交易的 total_value_usd 为 None 或很小")
    print("   2. 交易类型不匹配预期")
    print("   3. 重要性检查逻辑太严格")
    print("   4. 交易分析器返回的数据格式问题")
    
    print("\n🔧 调试建议:")
    print("   1. 检查实际运行日志中的 '检查交易重要性' 消息")
    print("   2. 确认交易类型和美元价值")
    print("   3. 临时降低阈值或放宽检查条件")
    print("   4. 确保 transfer_info 和 swap_info 有正确数据")

# 运行测试
test_monitoring_flow()

print("\n💡 临时解决方案:")
print("   如果需要立即看到效果，可以:")
print("   1. 在 _check_sol_transfer 中临时返回 True")
print("   2. 或者在 _is_important_transaction 中添加兜底逻辑")
print("   3. 查看实际的交易数据来调整阈值")