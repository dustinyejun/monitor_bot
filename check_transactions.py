#!/usr/bin/env python3
"""
检查 solana_transactions 表中的记录
"""

from src.config.database import SessionLocal
from src.models.solana import SolanaTransaction
from sqlalchemy import func, desc

def main():
    with SessionLocal() as db:
        # 统计记录数
        count = db.query(func.count(SolanaTransaction.id)).scalar()
        print(f'solana_transactions 表中的记录数: {count}')
        
        if count > 0:
            # 获取最新的几条记录
            latest_transactions = db.query(SolanaTransaction).order_by(desc(SolanaTransaction.created_at)).limit(5).all()
            
            print("\n最新的交易记录:")
            for tx in latest_transactions:
                print(f"- {tx.signature[:16]}... | {tx.transaction_type} | ${tx.amount_usd} | {tx.created_at}")
        else:
            print("表中暂无记录，说明还没有发现符合条件的重要交易")

if __name__ == "__main__":
    main()