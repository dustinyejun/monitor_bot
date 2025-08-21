"""
Solana监控服务
负责定时检查Solana钱包的交易记录，分析交易并存储到数据库
"""

import asyncio
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from sqlalchemy import select, and_, desc
from decimal import Decimal

from ..config.database import get_db_session, SessionLocal
from ..models.solana import SolanaWallet, SolanaTransaction
from ..schemas.solana import SolanaWalletCreate, SolanaWalletResponse, SolanaTransactionResponse
from .solana_client import SolanaClient, SolanaRPCError
from .solana_analyzer import SolanaAnalyzer, TransactionType, DEXPlatform
from ..utils.logger import logger


class SolanaMonitorService:
    """Solana监控服务"""
    
    def __init__(self):
        self.solana_client = None
        self.analyzer = SolanaAnalyzer()
        
    async def start_monitoring(self):
        """启动监控服务"""
        logger.info("启动Solana监控服务")
        
        async with SolanaClient() as client:
            self.solana_client = client
            
            # 检查RPC连接
            health = await client.get_health()
            if health != "ok":
                logger.error("Solana RPC节点不健康，监控服务可能不稳定")
            else:
                logger.info("Solana RPC连接正常")
                
            while True:
                try:
                    await self.check_all_wallets()
                    await asyncio.sleep(30)  # 每30秒检查一次
                except Exception as e:
                    logger.error(f"监控循环出错: {str(e)}")
                    await asyncio.sleep(10)  # 出错后等待10秒再继续
                    
    async def check_all_wallets(self):
        """检查所有激活钱包的新交易"""
        with SessionLocal() as db:
            # 获取所有激活的钱包
            active_wallets = db.execute(
                select(SolanaWallet).where(SolanaWallet.is_active == True)
            ).scalars().all()
            
            logger.info(f"开始检查 {len(active_wallets)} 个钱包")
            
            for wallet in active_wallets:
                try:
                    await self.check_wallet_transactions(db, wallet)
                except Exception as e:
                    logger.error(f"检查钱包 {wallet.address} 失败: {str(e)}")
                    
                # 避免API限制，钱包间添加延迟
                await asyncio.sleep(1)
                
    async def check_wallet_transactions(self, db: Session, wallet: SolanaWallet):
        """
        检查单个钱包的新交易
        
        Args:
            db: 数据库会话
            wallet: Solana钱包对象
        """
        try:
            logger.debug(f"检查钱包交易: {wallet.address}")
            
            # 获取最新的交易签名
            before_signature = wallet.last_signature if wallet.last_signature else None
            
            signatures = await self.solana_client.get_signatures_for_address(
                address=wallet.address,
                limit=50,
                before=before_signature
            )
            
            if not signatures:
                logger.debug(f"钱包 {wallet.address} 没有新交易")
                wallet.last_check_at = datetime.now(timezone.utc).isoformat()
                db.commit()
                return
                
            logger.info(f"钱包 {wallet.address} 发现 {len(signatures)} 个新交易")
            
            # 处理交易
            new_transactions = 0
            analyzed_transactions = 0
            
            for signature in signatures:
                # 检查交易是否已存在
                existing_tx = db.execute(
                    select(SolanaTransaction).where(SolanaTransaction.signature == signature)
                ).scalar_one_or_none()
                
                if existing_tx:
                    continue
                    
                try:
                    # 获取交易详情
                    tx_detail = await self.solana_client.get_transaction(signature)
                    if not tx_detail:
                        logger.warning(f"无法获取交易详情: {signature}")
                        continue
                        
                    # 分析交易
                    analysis_result = await self.analyzer.analyze_transaction(tx_detail)
                    
                    # 检查是否应该过滤此交易
                    if self._should_filter_transaction(analysis_result, wallet):
                        logger.debug(f"过滤交易: {signature}")
                        continue
                        
                    # 创建交易记录
                    transaction = SolanaTransaction(
                        signature=signature,
                        wallet_id=wallet.id,
                        slot=tx_detail.slot,
                        block_time=tx_detail.block_time,
                        is_success=tx_detail.is_success,
                        fee_lamports=tx_detail.fee or 0,
                        
                        # 分析结果
                        transaction_type=analysis_result.transaction_type.value,
                        dex_platform=analysis_result.dex_platform.value,
                        
                        # 交易详情
                        from_address=analysis_result.transfer_info.from_address if analysis_result.transfer_info else None,
                        to_address=analysis_result.transfer_info.to_address if analysis_result.transfer_info else None,
                        token_mint=analysis_result.transfer_info.token.mint if analysis_result.transfer_info else None,
                        amount=float(analysis_result.transfer_info.amount) if analysis_result.transfer_info else None,
                        amount_usd=float(analysis_result.total_value_usd) if analysis_result.total_value_usd else None,
                        
                        # 交换信息
                        swap_from_mint=analysis_result.swap_info.from_token.mint if analysis_result.swap_info else None,
                        swap_to_mint=analysis_result.swap_info.to_token.mint if analysis_result.swap_info else None,
                        swap_from_amount=float(analysis_result.swap_info.from_amount) if analysis_result.swap_info else None,
                        swap_to_amount=float(analysis_result.swap_info.to_amount) if analysis_result.swap_info else None,
                        
                        # 风险评估
                        risk_level=analysis_result.risk_level,
                        risk_factors=analysis_result.risk_factors,
                        
                        # 其他信息
                        raw_data={
                            'accounts': tx_detail.accounts,
                            'instructions': tx_detail.instructions[:5],  # 限制指令数量
                            'pre_balances': tx_detail.pre_balances,
                            'post_balances': tx_detail.post_balances
                        },
                        
                        is_processed=False,
                        is_notified=False
                    )
                    
                    db.add(transaction)
                    new_transactions += 1
                    analyzed_transactions += 1
                    
                    # 更新最新签名
                    if not wallet.last_signature or signature != wallet.last_signature:
                        wallet.last_signature = signature
                        
                except Exception as e:
                    logger.error(f"处理交易 {signature} 失败: {str(e)}")
                    continue
                    
            # 更新检查时间
            wallet.last_check_at = datetime.now(timezone.utc).isoformat()
            
            # 提交所有更改
            db.commit()
            
            logger.info(f"钱包 {wallet.address} 处理完成: 新交易 {new_transactions}, 已分析 {analyzed_transactions}")
            
        except SolanaRPCError as e:
            logger.error(f"Solana RPC错误 {wallet.address}: {e.message}")
        except Exception as e:
            logger.error(f"处理钱包 {wallet.address} 时出错: {str(e)}")
            db.rollback()
            
    def _should_filter_transaction(self, analysis_result, wallet: SolanaWallet) -> bool:
        """
        判断是否应该过滤此交易
        
        Args:
            analysis_result: 分析结果
            wallet: 钱包对象
            
        Returns:
            是否过滤
        """
        # 获取钱包的过滤配置
        exclude_tokens = wallet.exclude_tokens or []
        
        # 过滤指定代币
        if analysis_result.transfer_info:
            token_mint = analysis_result.transfer_info.token.mint
            if token_mint in exclude_tokens:
                return True
                
        if analysis_result.swap_info:
            from_mint = analysis_result.swap_info.from_token.mint
            to_mint = analysis_result.swap_info.to_token.mint
            if from_mint in exclude_tokens or to_mint in exclude_tokens:
                return True
                
        # 过滤失败的交易（可选）
        if not analysis_result.transaction.is_success:
            return False  # 暂时不过滤失败交易，用于分析
            
        # 过滤小额交易（可选）
        if analysis_result.total_value_usd and analysis_result.total_value_usd < Decimal('1'):
            return True
            
        return False
        
    def add_wallet(self, address: str, alias: str = None) -> SolanaWalletResponse:
        """
        添加新的监控钱包
        
        Args:
            address: 钱包地址
            alias: 钱包别名
            
        Returns:
            创建的钱包对象
        """
        with SessionLocal() as db:
            # 检查钱包是否已存在
            existing_wallet = db.execute(
                select(SolanaWallet).where(SolanaWallet.address == address)
            ).scalar_one_or_none()
            
            if existing_wallet:
                logger.warning(f"钱包已存在: {address}")
                return SolanaWalletResponse.model_validate(existing_wallet)
                
            # 创建新钱包
            wallet = SolanaWallet(
                address=address,
                alias=alias,
                is_active=True
            )
            
            db.add(wallet)
            db.commit()
            db.refresh(wallet)
            
            logger.info(f"添加新钱包: {address}")
            return SolanaWalletResponse.model_validate(wallet)
            
    def remove_wallet(self, address: str) -> bool:
        """
        移除监控钱包
        
        Args:
            address: 钱包地址
            
        Returns:
            是否成功移除
        """
        with SessionLocal() as db:
            wallet = db.execute(
                select(SolanaWallet).where(SolanaWallet.address == address)
            ).scalar_one_or_none()
            
            if not wallet:
                logger.warning(f"钱包不存在: {address}")
                return False
                
            db.delete(wallet)
            db.commit()
            
            logger.info(f"移除钱包: {address}")
            return True
            
    def update_wallet_status(self, address: str, is_active: bool) -> bool:
        """
        更新钱包监控状态
        
        Args:
            address: 钱包地址
            is_active: 是否激活
            
        Returns:
            是否成功更新
        """
        with SessionLocal() as db:
            wallet = db.execute(
                select(SolanaWallet).where(SolanaWallet.address == address)
            ).scalar_one_or_none()
            
            if not wallet:
                logger.warning(f"钱包不存在: {address}")
                return False
                
            wallet.is_active = is_active
            db.commit()
            
            status = "激活" if is_active else "停用"
            logger.info(f"{status}钱包监控: {address}")
            return True
            
    def update_wallet_exclude_tokens(self, address: str, exclude_tokens: List[str]) -> bool:
        """
        更新钱包排除代币列表
        
        Args:
            address: 钱包地址
            exclude_tokens: 排除的代币合约地址列表
            
        Returns:
            是否成功更新
        """
        with SessionLocal() as db:
            wallet = db.execute(
                select(SolanaWallet).where(SolanaWallet.address == address)
            ).scalar_one_or_none()
            
            if not wallet:
                logger.warning(f"钱包不存在: {address}")
                return False
                
            wallet.exclude_tokens = exclude_tokens
            db.commit()
            
            logger.info(f"更新钱包排除代币: {address} - {len(exclude_tokens)}个代币")
            return True
            
    def get_wallet_list(self, active_only: bool = False) -> List[SolanaWalletResponse]:
        """
        获取钱包列表
        
        Args:
            active_only: 是否只返回活跃钱包
            
        Returns:
            钱包列表
        """
        with SessionLocal() as db:
            query = select(SolanaWallet)
            if active_only:
                query = query.where(SolanaWallet.is_active == True)
                
            wallets = db.execute(query).scalars().all()
            return [SolanaWalletResponse.model_validate(wallet) for wallet in wallets]
    
    def get_active_wallets(self) -> List[SolanaWallet]:
        """
        获取活跃的钱包列表（直接返回模型对象）
        
        Returns:
            活跃钱包列表
        """
        with SessionLocal() as db:
            wallets = db.execute(
                select(SolanaWallet).where(SolanaWallet.is_active == True)
            ).scalars().all()
            return list(wallets)
            
    def get_wallet_transactions(
        self, 
        address: str, 
        limit: int = 50, 
        transaction_type: str = None
    ) -> List[SolanaTransactionResponse]:
        """
        获取钱包交易记录
        
        Args:
            address: 钱包地址
            limit: 返回数量限制
            transaction_type: 交易类型过滤
            
        Returns:
            交易记录列表
        """
        with SessionLocal() as db:
            # 获取钱包
            wallet = db.execute(
                select(SolanaWallet).where(SolanaWallet.address == address)
            ).scalar_one_or_none()
            
            if not wallet:
                return []
                
            # 构建查询
            query = select(SolanaTransaction).where(SolanaTransaction.wallet_id == wallet.id)
            
            if transaction_type:
                query = query.where(SolanaTransaction.transaction_type == transaction_type)
                
            query = query.order_by(desc(SolanaTransaction.created_at)).limit(limit)
            
            transactions = db.execute(query).scalars().all()
            return [SolanaTransactionResponse.model_validate(tx) for tx in transactions]
            
    def get_unprocessed_transactions(self, limit: int = 50) -> List[Dict[str, Any]]:
        """
        获取未处理的交易
        
        Args:
            limit: 返回数量限制
            
        Returns:
            交易列表
        """
        with SessionLocal() as db:
            transactions = db.execute(
                select(SolanaTransaction, SolanaWallet)
                .join(SolanaWallet, SolanaTransaction.wallet_id == SolanaWallet.id)
                .where(SolanaTransaction.is_processed == False)
                .order_by(desc(SolanaTransaction.created_at))
                .limit(limit)
            ).all()
            
            result = []
            for tx, wallet in transactions:
                result.append({
                    'signature': tx.signature,
                    'wallet_address': wallet.address,
                    'wallet_label': wallet.label,
                    'transaction_type': tx.transaction_type,
                    'dex_platform': tx.dex_platform,
                    'amount_usd': tx.amount_usd,
                    'risk_level': tx.risk_level,
                    'created_at': tx.created_at,
                    'block_time': tx.block_time
                })
                
            return result
            
    def mark_transactions_processed(self, signatures: List[str]):
        """
        标记交易为已处理
        
        Args:
            signatures: 交易签名列表
        """
        with SessionLocal() as db:
            db.execute(
                SolanaTransaction.__table__.update()
                .where(SolanaTransaction.signature.in_(signatures))
                .values(is_processed=True)
            )
            db.commit()
            
            logger.info(f"标记 {len(signatures)} 条交易为已处理")
            
    def mark_transactions_notified(self, signatures: List[str]):
        """
        标记交易为已通知
        
        Args:
            signatures: 交易签名列表
        """
        with SessionLocal() as db:
            db.execute(
                SolanaTransaction.__table__.update()
                .where(SolanaTransaction.signature.in_(signatures))
                .values(is_notified=True)
            )
            db.commit()
            
            logger.info(f"标记 {len(signatures)} 条交易为已通知")
    
    def update_wallet_check_info(self, address: str, last_signature: str, check_time: datetime):
        """
        更新钱包的检查信息
        
        Args:
            address: 钱包地址
            last_signature: 最新的交易签名
            check_time: 检查时间
        """
        with SessionLocal() as db:
            wallet = db.execute(
                select(SolanaWallet).where(SolanaWallet.address == address)
            ).scalar_one_or_none()
            
            if wallet:
                wallet.last_signature = last_signature
                wallet.last_check_at = check_time.isoformat()
                db.commit()
                logger.debug(f"更新钱包检查信息: {address}")
            else:
                logger.warning(f"钱包不存在: {address}")
    
    def update_wallet_check_time(self, address: str, check_time: datetime):
        """
        更新钱包的检查时间
        
        Args:
            address: 钱包地址
            check_time: 检查时间
        """
        with SessionLocal() as db:
            wallet = db.execute(
                select(SolanaWallet).where(SolanaWallet.address == address)
            ).scalar_one_or_none()
            
            if wallet:
                wallet.last_check_at = check_time.isoformat()
                db.commit()
                logger.debug(f"更新钱包检查时间: {address}")
            else:
                logger.warning(f"钱包不存在: {address}")
    
    def is_transaction_processed(self, signature: str) -> bool:
        """
        检查交易是否已经处理过
        
        Args:
            signature: 交易签名
            
        Returns:
            True if 交易已处理，False otherwise
        """
        try:
            with SessionLocal() as db:
                existing_tx = db.execute(
                    select(SolanaTransaction).where(SolanaTransaction.signature == signature)
                ).scalar_one_or_none()
                
                return existing_tx is not None
                
        except Exception as e:
            logger.error(f"检查交易是否已处理失败: {str(e)}")
            # 如果检查失败，为安全起见认为已处理，避免重复处理
            return True

    async def save_transaction_analysis(self, analysis):
        """
        保存交易分析结果到数据库
        
        Args:
            analysis: 交易分析结果
        """
        try:
            with SessionLocal() as db:
                # 从 analysis.transaction 对象获取交易签名
                signature = analysis.transaction.signature
                
                # 检查交易是否已存在
                existing_tx = db.execute(
                    select(SolanaTransaction).where(SolanaTransaction.signature == signature)
                ).scalar_one_or_none()
                
                if existing_tx:
                    logger.debug(f"交易已存在: {signature}")
                    return
                
                # 获取钱包ID（从分析结果或者通过其他方式获取钱包地址）
                wallet_address = getattr(analysis, 'wallet_address', None)
                if not wallet_address:
                    # 如果分析结果中没有钱包地址，可能需要从其他地方获取
                    logger.warning(f"分析结果中缺少钱包地址: {signature}")
                    return
                    
                wallet = db.execute(
                    select(SolanaWallet).where(SolanaWallet.address == wallet_address)
                ).scalar_one_or_none()
                
                if not wallet:
                    logger.warning(f"找不到钱包: {wallet_address}")
                    return
                
                # 从交易分析结果中获取相关属性
                token_address = None
                token_symbol = None
                token_name = None
                amount = None
                
                if analysis.transfer_info:
                    token_address = analysis.transfer_info.token.mint
                    token_symbol = analysis.transfer_info.token.symbol
                    token_name = analysis.transfer_info.token.name
                    amount = analysis.transfer_info.amount
                elif analysis.swap_info:
                    token_address = analysis.swap_info.to_token.mint
                    token_symbol = analysis.swap_info.to_token.symbol
                    token_name = analysis.swap_info.to_token.name
                    amount = analysis.swap_info.to_amount
                
                # 转换 block_time (Unix 时间戳) 为 datetime
                block_time_dt = None
                if hasattr(analysis.transaction, 'block_time') and analysis.transaction.block_time:
                    block_time_dt = datetime.fromtimestamp(analysis.transaction.block_time)
                
                # 创建交易记录
                transaction = SolanaTransaction(
                    signature=signature,
                    wallet_id=wallet.id,
                    transaction_type=analysis.transaction_type.value,
                    status="confirmed",
                    token_address=token_address,
                    token_symbol=token_symbol,
                    token_name=token_name,
                    amount=amount,
                    amount_usd=analysis.total_value_usd,
                    block_time=block_time_dt,
                    dex_name=analysis.dex_platform.value if analysis.dex_platform else None,
                    solscan_url=f"https://solscan.io/tx/{signature}",
                    is_processed=True,
                    is_notified=False
                )
                
                db.add(transaction)
                db.commit()
                logger.info(f"保存交易分析结果: {signature}")
                
        except Exception as e:
            logger.error(f"保存交易分析失败: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            
    async def get_wallet_balance(self, address: str) -> Dict[str, Any]:
        """
        获取钱包余额信息
        
        Args:
            address: 钱包地址
            
        Returns:
            余额信息
        """
        try:
            async with SolanaClient() as client:
                # 获取SOL余额
                sol_balance = await client.get_balance(address)
                
                # 获取代币余额
                token_accounts = await client.get_token_accounts(address)
                
                return {
                    'address': address,
                    'sol_balance': float(Decimal(sol_balance) / Decimal(10**9)),
                    'tokens': [
                        {
                            'mint': token.mint,
                            'amount': float(token.balance),
                            'ui_amount': token.ui_amount
                        }
                        for token in token_accounts
                    ],
                    'total_tokens': len(token_accounts)
                }
                
        except Exception as e:
            logger.error(f"获取钱包余额失败 {address}: {str(e)}")
            return {'error': str(e)}
            
    def get_statistics(self) -> Dict[str, Any]:
        """
        获取监控统计信息
        
        Returns:
            统计数据
        """
        with SessionLocal() as db:
            # 钱包统计
            total_wallets = db.execute(select(SolanaWallet)).scalars().all()
            active_wallets = [w for w in total_wallets if w.is_active]
            
            # 交易统计
            all_transactions = db.execute(select(SolanaTransaction)).scalars().all()
            successful_txs = [t for t in all_transactions if t.is_success]
            
            # 今日统计
            today = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
            today_txs = [t for t in all_transactions if t.created_at >= today]
            
            # 按类型统计
            type_counts = {}
            for tx in all_transactions:
                tx_type = tx.transaction_type
                type_counts[tx_type] = type_counts.get(tx_type, 0) + 1
                
            # 按DEX平台统计
            dex_counts = {}
            for tx in all_transactions:
                if tx.dex_platform and tx.dex_platform != 'unknown':
                    dex_counts[tx.dex_platform] = dex_counts.get(tx.dex_platform, 0) + 1
                    
            # 价值统计
            total_value = sum([tx.amount_usd for tx in all_transactions if tx.amount_usd])
            
            return {
                'total_wallets': len(total_wallets),
                'active_wallets': len(active_wallets),
                'total_transactions': len(all_transactions),
                'successful_transactions': len(successful_txs),
                'success_rate': len(successful_txs) / len(all_transactions) if all_transactions else 0,
                'today_transactions': len(today_txs),
                'transaction_types': type_counts,
                'dex_platforms': dex_counts,
                'total_value_usd': total_value,
                'unprocessed_transactions': len([t for t in all_transactions if not t.is_processed]),
                'unnotified_transactions': len([t for t in all_transactions if not t.is_notified])
            }