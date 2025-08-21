"""
Solana交易统计服务
用于计算钱包购买笔数等统计信息
"""
from typing import Dict, Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_, func
from loguru import logger

from ..config.database import SessionLocal
from ..models.solana import SolanaTransaction, SolanaWallet


class SolanaTransactionStatsService:
    """Solana交易统计服务"""
    
    def __init__(self):
        pass
    
    def get_wallet_token_purchase_count(self, wallet_address: str, token_address: str) -> int:
        """
        获取指定钱包对指定代币的购买笔数
        
        Args:
            wallet_address: 钱包地址
            token_address: 代币合约地址
            
        Returns:
            int: 购买笔数
        """
        db = SessionLocal()
        try:
            # 查找钱包ID
            wallet = db.query(SolanaWallet).filter(
                SolanaWallet.address == wallet_address
            ).first()
            
            if not wallet:
                logger.warning(f"未找到钱包: {wallet_address}")
                return 0
            
            # 统计购买笔数（交易类型为buy或swap的交易）
            purchase_count = db.query(SolanaTransaction).filter(
                and_(
                    SolanaTransaction.wallet_id == wallet.id,
                    SolanaTransaction.token_address == token_address,
                    SolanaTransaction.transaction_type.in_(['buy', 'swap']),
                    SolanaTransaction.status == 'confirmed'
                )
            ).count()
            
            return purchase_count
            
        except Exception as e:
            logger.error(f"获取购买笔数失败: {e}")
            return 0
        finally:
            db.close()
    
    def get_wallet_token_stats(self, wallet_address: str, token_address: str) -> Dict:
        """
        获取钱包对指定代币的详细统计
        
        Args:
            wallet_address: 钱包地址
            token_address: 代币合约地址
            
        Returns:
            Dict: 统计信息，包含总投资金额和数量
        """
        db = SessionLocal()
        try:
            # 查找钱包
            wallet = db.query(SolanaWallet).filter(
                SolanaWallet.address == wallet_address
            ).first()
            
            if not wallet:
                return {
                    "purchase_count": 0,
                    "total_token_amount": 0,
                    "total_invested_usd": 0,
                    "avg_purchase_usd": 0,
                    "first_purchase_time": None,
                    "last_purchase_time": None
                }
            
            # 查询购买交易
            purchase_transactions = db.query(SolanaTransaction).filter(
                and_(
                    SolanaTransaction.wallet_id == wallet.id,
                    SolanaTransaction.token_address == token_address,
                    SolanaTransaction.transaction_type.in_(['buy', 'swap']),
                    SolanaTransaction.status == 'confirmed'
                )
            ).all()
            
            if not purchase_transactions:
                return {
                    "purchase_count": 0,
                    "total_token_amount": 0,
                    "total_invested_usd": 0,
                    "avg_purchase_usd": 0,
                    "first_purchase_time": None,
                    "last_purchase_time": None
                }
            
            # 计算统计信息
            purchase_count = len(purchase_transactions)
            total_token_amount = sum(float(tx.amount or 0) for tx in purchase_transactions)
            total_invested_usd = sum(float(tx.amount_usd or 0) for tx in purchase_transactions)
            avg_purchase_usd = total_invested_usd / purchase_count if purchase_count > 0 else 0
            
            # 时间统计
            purchase_times = [tx.block_time for tx in purchase_transactions if tx.block_time]
            first_purchase_time = min(purchase_times) if purchase_times else None
            last_purchase_time = max(purchase_times) if purchase_times else None
            
            return {
                "purchase_count": purchase_count,
                "total_token_amount": total_token_amount,
                "total_invested_usd": total_invested_usd,
                "avg_purchase_usd": avg_purchase_usd,
                "first_purchase_time": first_purchase_time,
                "last_purchase_time": last_purchase_time
            }
            
        except Exception as e:
            logger.error(f"获取钱包代币统计失败: {e}")
            return {
                "purchase_count": 0,
                "total_token_amount": 0,
                "total_invested_usd": 0,
                "avg_purchase_usd": 0,
                "first_purchase_time": None,
                "last_purchase_time": None
            }
        finally:
            db.close()
    
    def calculate_next_purchase_count(self, wallet_address: str, token_address: str) -> int:
        """
        计算下一笔交易的购买笔数（当前笔数+1）
        
        Args:
            wallet_address: 钱包地址
            token_address: 代币合约地址
            
        Returns:
            int: 下一笔购买的序号
        """
        current_count = self.get_wallet_token_purchase_count(wallet_address, token_address)
        return current_count + 1
    
    def get_wallet_top_tokens(self, wallet_address: str, limit: int = 10) -> list:
        """
        获取钱包购买最多的代币排行榜
        
        Args:
            wallet_address: 钱包地址
            limit: 返回数量限制
            
        Returns:
            list: 代币购买排行
        """
        db = SessionLocal()
        try:
            # 查找钱包
            wallet = db.query(SolanaWallet).filter(
                SolanaWallet.address == wallet_address
            ).first()
            
            if not wallet:
                return []
            
            # 按代币分组统计购买次数
            token_stats = db.query(
                SolanaTransaction.token_address,
                SolanaTransaction.token_symbol,
                SolanaTransaction.token_name,
                func.count(SolanaTransaction.id).label('purchase_count'),
                func.sum(SolanaTransaction.amount_usd).label('total_spent_usd')
            ).filter(
                and_(
                    SolanaTransaction.wallet_id == wallet.id,
                    SolanaTransaction.transaction_type.in_(['buy', 'swap']),
                    SolanaTransaction.status == 'confirmed',
                    SolanaTransaction.token_address.isnot(None)
                )
            ).group_by(
                SolanaTransaction.token_address,
                SolanaTransaction.token_symbol,
                SolanaTransaction.token_name
            ).order_by(
                func.count(SolanaTransaction.id).desc()
            ).limit(limit).all()
            
            return [
                {
                    "token_address": stat.token_address,
                    "token_symbol": stat.token_symbol,
                    "token_name": stat.token_name,
                    "purchase_count": stat.purchase_count,
                    "total_spent_usd": float(stat.total_spent_usd or 0)
                }
                for stat in token_stats
            ]
            
        except Exception as e:
            logger.error(f"获取钱包代币排行失败: {e}")
            return []
        finally:
            db.close()
    
    def get_notification_variables(self, wallet_address: str, token_address: str, current_transaction: Dict) -> Dict:
        """
        获取通知所需的所有变量，包括统计信息
        
        Args:
            wallet_address: 钱包地址
            token_address: 代币CA地址
            current_transaction: 当前交易信息
            
        Returns:
            Dict: 完整的通知变量字典
        """
        try:
            # 获取钱包统计
            stats = self.get_wallet_token_stats(wallet_address, token_address)
            
            # 计算包含当前交易的统计（假设当前交易是买入）
            if current_transaction.get('transaction_type') in ['buy', 'swap']:
                current_amount = float(current_transaction.get('amount', 0))
                current_usd = float(current_transaction.get('amount_usd', 0))
                
                # 更新统计（包含当前交易）
                new_total_amount = stats['total_token_amount'] + current_amount
                new_total_usd = stats['total_invested_usd'] + current_usd
                new_count = stats['purchase_count'] + 1
                new_avg_usd = new_total_usd / new_count if new_count > 0 else 0
            else:
                # 非买入交易，使用历史统计
                new_total_amount = stats['total_token_amount']
                new_total_usd = stats['total_invested_usd']
                new_count = stats['purchase_count']
                new_avg_usd = stats['avg_purchase_usd']
            
            # 构造完整的通知变量
            notification_vars = {
                # 当前交易信息
                'wallet_alias': current_transaction.get('wallet_alias', 'Unknown Wallet'),
                'transaction_type': current_transaction.get('transaction_type', 'unknown'),
                'amount': current_transaction.get('amount', '0'),
                'token_symbol': current_transaction.get('token_symbol', 'Unknown'),
                'amount_usd': current_transaction.get('amount_usd', 0),
                'token_name': current_transaction.get('token_name', 'Unknown Token'),
                'token_address': token_address,
                'signature': current_transaction.get('signature', ''),
                'solscan_url': current_transaction.get('solscan_url', ''),
                'block_time': current_transaction.get('block_time', ''),
                
                # 统计信息
                'purchase_count': str(new_count),
                'total_token_amount': f'{new_total_amount:,.0f}',  # 格式化大数字
                'total_invested_usd': new_total_usd,
                'avg_purchase_usd': new_avg_usd
            }
            
            return notification_vars
            
        except Exception as e:
            logger.error(f"获取通知变量失败: {e}")
            # 返回基础变量，避免通知失败
            return {
                'wallet_alias': current_transaction.get('wallet_alias', 'Unknown Wallet'),
                'transaction_type': current_transaction.get('transaction_type', 'unknown'),
                'amount': current_transaction.get('amount', '0'),
                'token_symbol': current_transaction.get('token_symbol', 'Unknown'),
                'amount_usd': current_transaction.get('amount_usd', 0),
                'token_name': current_transaction.get('token_name', 'Unknown Token'),
                'token_address': token_address,
                'signature': current_transaction.get('signature', ''),
                'solscan_url': current_transaction.get('solscan_url', ''),
                'block_time': current_transaction.get('block_time', ''),
                'purchase_count': '1',
                'total_token_amount': current_transaction.get('amount', '0'),
                'total_invested_usd': current_transaction.get('amount_usd', 0),
                'avg_purchase_usd': current_transaction.get('amount_usd', 0)
            }


# 全局统计服务实例
solana_stats_service = SolanaTransactionStatsService()