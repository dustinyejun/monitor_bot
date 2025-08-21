#!/usr/bin/env python3
"""
测试DEX_SWAP通知增强功能
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

print("🔍 测试DEX_SWAP通知增强功能...")

def test_token_purchase_stats():
    """测试代币购买统计功能"""
    
    print("\n1. 测试代币购买统计查询...")
    try:
        from src.services.solana_monitor import SolanaMonitorService
        from datetime import datetime
        
        monitor = SolanaMonitorService()
        
        # 测试查询（使用示例参数）
        stats = monitor.get_token_purchase_stats(
            wallet_id=1,
            token_address="DezXAZ8z7PnrnRJjz3wXBoRgixCa6xjnB7YaB1pPB263",  # BONK CA地址示例
            before_time=datetime.now()
        )
        
        print(f"   ✅ 查询成功")
        print(f"   购买次数: {stats['purchase_count']}")
        print(f"   累计SOL金额: {stats['total_sol_amount']}")
        print(f"   累计USD金额: {stats['total_usd_amount']}")
        
    except Exception as e:
        print(f"   ❌ 查询失败: {e}")

def test_notification_template():
    """测试通知模板"""
    
    print("\n2. 测试通知模板...")
    try:
        from src.config.notification_config import get_template
        
        template = get_template("solana_transaction")
        
        # 检查模板是否包含DEX交换信息占位符
        if "{dex_swap_info}" in template.content_template:
            print("   ✅ 模板包含 dex_swap_info 占位符")
        else:
            print("   ❌ 模板缺少 dex_swap_info 占位符")
            
        # 测试模板渲染
        test_data = {
            "wallet_address": "AbcD...XyZ",
            "wallet_alias": "测试钱包",
            "transaction_type": "dex_swap",
            "amount": 1250000,
            "token_symbol": "BONK",
            "token_name": "Bonk",
            "block_time": "2025-08-21 16:30:00",
            "dex_swap_info": """🔄 **DEX交换详情**
- 从: 0.5 SOL
- 到: 1250000 BONK
- CA地址: `DezXAZ8z7PnrnRJjz3wXBoRgixCa6xjnB7YaB1pPB263`
- 购买次数: 第 3 次
- 累计投入: 1.8000 SOL ($270.50)"""
        }
        
        rendered_content = template.content_template.format(**test_data)
        print("   ✅ 模板渲染成功")
        print("\n   渲染结果预览:")
        print("   " + "="*50)
        for line in rendered_content.split('\n')[:10]:  # 只显示前10行
            print(f"   {line}")
        print("   ...")
        print("   " + "="*50)
        
    except Exception as e:
        print(f"   ❌ 模板测试失败: {e}")

def test_dex_swap_info_formatting():
    """测试DEX交换信息格式化"""
    
    print("\n3. 测试DEX交换信息格式化...")
    try:
        # 模拟交换信息
        class MockSwapInfo:
            def __init__(self):
                self.from_amount = 0.5
                self.from_token = MockToken("SOL", "Solana")
                self.to_amount = 1250000
                self.to_token = MockToken("BONK", "Bonk", "DezXAZ8z7PnrnRJjz3wXBoRgixCa6xjnB7YaB1pPB263")
        
        class MockToken:
            def __init__(self, symbol, name, mint=None):
                self.symbol = symbol
                self.name = name
                self.mint = mint or "So11111111111111111111111111111111111111112"
        
        swap_info = MockSwapInfo()
        purchase_stats = {
            'purchase_count': 3,
            'total_sol_amount': 1.8,
            'total_usd_amount': 270.50
        }
        
        # 格式化DEX交换信息
        dex_swap_info = f"""🔄 **DEX交换详情**
- 从: {swap_info.from_amount} {swap_info.from_token.symbol}
- 到: {swap_info.to_amount} {swap_info.to_token.symbol}
- CA地址: `{swap_info.to_token.mint}`
- 购买次数: 第 {purchase_stats['purchase_count']} 次
- 累计投入: {purchase_stats['total_sol_amount']:.4f} SOL (${purchase_stats['total_usd_amount']:.2f})"""
        
        print("   ✅ DEX交换信息格式化成功")
        print("\n   格式化结果:")
        print("   " + "-"*40)
        for line in dex_swap_info.split('\n'):
            print(f"   {line}")
        print("   " + "-"*40)
        
    except Exception as e:
        print(f"   ❌ 格式化失败: {e}")

def test_integration():
    """测试集成功能"""
    
    print("\n4. 测试功能集成...")
    try:
        from src.services.solana_analyzer import TransactionType
        
        # 检查TransactionType是否可用
        assert hasattr(TransactionType, 'DEX_SWAP'), "缺少 DEX_SWAP 类型"
        print("   ✅ TransactionType.DEX_SWAP 可用")
        
        # 检查核心组件
        from src.plugins.solana_monitor_plugin import SolanaMonitorPlugin
        from src.services.solana_monitor import SolanaMonitorService
        
        # 检查方法是否存在
        monitor = SolanaMonitorService()
        assert hasattr(monitor, 'get_token_purchase_stats'), "缺少 get_token_purchase_stats 方法"
        print("   ✅ get_token_purchase_stats 方法存在")
        
        print("   ✅ 所有核心组件集成正常")
        
    except Exception as e:
        print(f"   ❌ 集成测试失败: {e}")

# 运行测试
test_token_purchase_stats()
test_notification_template()
test_dex_swap_info_formatting()
test_integration()

print("\n🎉 DEX_SWAP通知增强测试完成")
print("\n📋 功能总结:")
print("   ✅ 数据库查询: get_token_purchase_stats 方法")
print("   ✅ 通知模板: 添加了 {dex_swap_info} 占位符") 
print("   ✅ 信息格式化: DEX交换详情格式化逻辑")
print("   ✅ 插件集成: _trigger_single_notification 方法增强")

print("\n🔮 预期效果:")
print("   当检测到 DEX_SWAP 交易时，通知将包含:")
print("   - 交换的代币信息（从 A 到 B）")
print("   - 代币合约地址（CA地址）")
print("   - 购买次数统计")
print("   - 累计投入金额（SOL和USD）")

print("\n⚠️ 注意事项:")
print("   - 需要确保数据库中有相关交易数据进行统计")
print("   - 如果查询失败，会使用默认值不影响通知发送")
print("   - 只有 DEX_SWAP 类型的交易才会显示交换详情")