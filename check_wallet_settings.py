#!/usr/bin/env python3
"""
检查钱包的最小金额设置
"""

from src.services.solana_monitor import SolanaMonitorService

def main():
    monitor = SolanaMonitorService()
    wallets = monitor.get_active_wallets()
    
    print("当前活跃钱包的设置:")
    for wallet in wallets:
        print(f'钱包: {wallet.address[:8]}...{wallet.address[-8:]}')
        print(f'  别名: {wallet.alias}')
        print(f'  最小金额阈值: ${wallet.min_amount_usd}')
        print()

if __name__ == "__main__":
    main()