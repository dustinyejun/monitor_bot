#!/usr/bin/env python3
"""
解释Solana监控机制
"""

from src.services.solana_monitor import SolanaMonitorService
from src.config.database import SessionLocal
from src.models.solana import SolanaWallet
from sqlalchemy import select

def explain_monitoring():
    """解释监控机制"""
    print("🔍 Solana交易监控机制详解")
    print("=" * 50)
    
    # 1. 查看监控的钱包
    monitor = SolanaMonitorService()
    wallets = monitor.get_active_wallets()
    
    print(f"\n1️⃣ 监控的钱包数量: {len(wallets)}")
    for wallet in wallets:
        print(f"   钱包: {wallet.address[:8]}...{wallet.address[-8:]}")
        print(f"   别名: {wallet.alias}")
        print(f"   最小金额阈值: ${wallet.min_amount_usd}")
        print(f"   上次检查签名: {wallet.last_signature[:8] + '...' if wallet.last_signature else 'None'}")
        print(f"   上次检查时间: {wallet.last_check_at}")
        print()
    
    print("\n2️⃣ 每30秒执行的监控流程:")
    print("   ┌─ 步骤1: 获取活跃钱包列表")
    print("   ├─ 步骤2: 对每个钱包调用 getSignaturesForAddress")
    print("   │   ├─ 参数: address = 钱包地址")
    print("   │   ├─ 参数: limit = 20 (最多获取20笔交易)")
    print("   │   ├─ 参数: before = last_signature (只获取新交易)")
    print("   │   └─ 参数: commitment = 'confirmed'")
    print("   ├─ 步骤3: 对每个交易签名调用 getTransaction")
    print("   ├─ 步骤4: 分析交易内容(金额、类型、代币等)")
    print("   ├─ 步骤5: 筛选重要交易(基于钱包的min_amount_usd)")
    print("   ├─ 步骤6: 保存重要交易到数据库")
    print("   ├─ 步骤7: 更新钱包的last_signature和last_check")
    print("   └─ 步骤8: 触发通知系统")
    
    print("\n3️⃣ RPC调用示例:")
    print("   🔗 getSignaturesForAddress:")
    print(f"      地址: {wallets[0].address if wallets else 'No wallet'}")
    print("      返回: 最新20笔交易的签名列表")
    print("      作用: 只获取新的交易(基于last_signature)")
    print()
    print("   🔗 getTransaction:")
    print("      输入: 交易签名")
    print("      返回: 交易完整信息(金额、代币、时间等)")
    print("      作用: 获取交易详情用于分析")
    
    print("\n4️⃣ 增量监控机制:")
    print("   💡 关键: 使用 'before' 参数实现增量获取")
    print("   💡 首次: before=None, 获取最新20笔交易")
    print("   💡 后续: before=last_signature, 只获取新交易")
    print("   💡 避免: 重复处理已经分析过的交易")
    
    print("\n5️⃣ 监控效果:")
    print("   ✅ 实时检测: 30秒内发现新交易")
    print("   ✅ 智能筛选: 只处理符合阈值的重要交易")
    print("   ✅ 去重机制: 不会重复处理相同交易")
    print("   ✅ 持久化: 交易记录保存到数据库")

if __name__ == "__main__":
    explain_monitoring()