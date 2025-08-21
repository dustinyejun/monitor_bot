#!/usr/bin/env python3
"""
更新钱包的最小金额阈值
"""

from src.services.solana_monitor import SolanaMonitorService
from src.config.database import SessionLocal
from src.models.solana import SolanaWallet
from decimal import Decimal

def main():
    # 将测试钱包的阈值设置为 0.01 USD，以便测试数据库插入
    test_threshold = Decimal("0.01")
    
    with SessionLocal() as db:
        # 更新所有钱包的阈值用于测试
        wallets = db.query(SolanaWallet).filter(SolanaWallet.is_active == True).all()
        
        for wallet in wallets:
            old_threshold = wallet.min_amount_usd
            wallet.min_amount_usd = test_threshold
            print(f"更新钱包 {wallet.alias}: ${old_threshold} -> ${test_threshold}")
        
        db.commit()
        print(f"\n已将 {len(wallets)} 个活跃钱包的阈值更新为 ${test_threshold}")

if __name__ == "__main__":
    main()