#!/usr/bin/env python3
"""
添加测试钱包用于监控
"""

from src.services.solana_monitor import SolanaMonitorService
from src.utils.logger import logger

def main():
    """添加测试钱包"""
    monitor = SolanaMonitorService()
    
    # 添加一个测试钱包 (Raydium官方钱包地址)
    test_wallet = "5Q544fKrFoe6tsEbD7S8EmxGTJYAKtTVhAW5Q5pge4j1"
    
    try:
        result = monitor.add_wallet(test_wallet, "Raydium官方测试")
        logger.info(f"添加测试钱包成功: {result.address}")
        logger.info(f"钱包别名: {result.alias}")
        
        # 获取钱包列表验证
        wallets = monitor.get_active_wallets()
        logger.info(f"当前活跃钱包数量: {len(wallets)}")
        for wallet in wallets:
            logger.info(f"- {wallet.address[:8]}...{wallet.address[-8:]} ({wallet.alias})")
            
    except Exception as e:
        logger.error(f"添加测试钱包失败: {str(e)}")

if __name__ == "__main__":
    main()