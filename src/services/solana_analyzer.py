"""
Solana交易分析器
负责分析Solana交易，识别DEX交易、代币转账等，并计算价值
"""

import re
import asyncio
import aiohttp
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
from decimal import Decimal
import json
from datetime import datetime

from .solana_client import SolanaTransaction, SolanaTokenInfo
from ..utils.logger import logger


class TransactionType(Enum):
    """交易类型"""
    UNKNOWN = "unknown"
    SOL_TRANSFER = "sol_transfer"
    TOKEN_TRANSFER = "token_transfer"
    DEX_SWAP = "dex_swap"
    DEX_ADD_LIQUIDITY = "dex_add_liquidity"
    DEX_REMOVE_LIQUIDITY = "dex_remove_liquidity"
    TOKEN_MINT = "token_mint"
    TOKEN_BURN = "token_burn"
    PROGRAM_INTERACTION = "program_interaction"


class DEXPlatform(Enum):
    """DEX平台"""
    UNKNOWN = "unknown"
    RAYDIUM = "raydium"
    JUPITER = "jupiter"
    ORCA = "orca"
    SERUM = "serum"
    SABER = "saber"
    MERCURIAL = "mercurial"
    ALDRIN = "aldrin"


@dataclass
class TokenInfo:
    """代币信息"""
    mint: str
    symbol: str = ""
    name: str = ""
    decimals: int = 9
    logo_url: str = ""
    price_usd: Optional[Decimal] = None
    market_cap: Optional[Decimal] = None
    
    def __post_init__(self):
        if self.price_usd is not None and isinstance(self.price_usd, (int, float, str)):
            self.price_usd = Decimal(str(self.price_usd))


@dataclass
class SwapInfo:
    """交换信息"""
    from_token: TokenInfo
    to_token: TokenInfo
    from_amount: Decimal
    to_amount: Decimal
    from_amount_usd: Optional[Decimal] = None
    to_amount_usd: Optional[Decimal] = None
    price_impact: Optional[Decimal] = None
    
    def __post_init__(self):
        # 转换数值类型
        if isinstance(self.from_amount, (int, float, str)):
            self.from_amount = Decimal(str(self.from_amount))
        if isinstance(self.to_amount, (int, float, str)):
            self.to_amount = Decimal(str(self.to_amount))


@dataclass
class TransferInfo:
    """转账信息"""
    from_address: str
    to_address: str
    token: TokenInfo
    amount: Decimal
    amount_usd: Optional[Decimal] = None
    # 新增字段用于SOL_TRANSFER功能增强
    direction: Optional[str] = None  # 'in' 或 'out'，相对于监控钱包
    counterpart_address: Optional[str] = None  # 对方钱包地址
    counterpart_label: Optional[str] = None  # 对方地址标签
    
    def __post_init__(self):
        if isinstance(self.amount, (int, float, str)):
            self.amount = Decimal(str(self.amount))


@dataclass
class AnalysisResult:
    """交易分析结果"""
    transaction: SolanaTransaction
    transaction_type: TransactionType
    dex_platform: DEXPlatform = DEXPlatform.UNKNOWN
    
    # 不同类型交易的具体信息
    swap_info: Optional[SwapInfo] = None
    transfer_info: Optional[TransferInfo] = None
    
    # 通用信息
    total_value_usd: Optional[Decimal] = None
    gas_fee_sol: Optional[Decimal] = None
    gas_fee_usd: Optional[Decimal] = None
    
    # 风险评估
    risk_level: str = "low"  # low, medium, high
    risk_factors: List[str] = field(default_factory=list)
    
    def __post_init__(self):
        if self.total_value_usd is not None and isinstance(self.total_value_usd, (int, float, str)):
            self.total_value_usd = Decimal(str(self.total_value_usd))
        if self.gas_fee_sol is not None and isinstance(self.gas_fee_sol, (int, float, str)):
            self.gas_fee_sol = Decimal(str(self.gas_fee_sol))
        if self.gas_fee_usd is not None and isinstance(self.gas_fee_usd, (int, float, str)):
            self.gas_fee_usd = Decimal(str(self.gas_fee_usd))


class SolanaAnalyzer:
    """Solana交易分析器"""
    
    def __init__(self):
        # 已知程序ID
        self.known_programs = {
            # DEX Programs
            "9WzDXwBbmkg8ZTbNMqUxvQRAyrZzDsGYdLVL9zYtAWWM": DEXPlatform.RAYDIUM,
            "JUP2jxvXaqu7NQY1GmNF4m1vodw12LVXYxbFL2uJvfo": DEXPlatform.JUPITER,
            "DjVE6JNiYqPL2QXyCUUh8rNjHrbz9hXHNYt99MQ59qw1": DEXPlatform.ORCA,
            "9xQeWvG816bUx9EPjHmaT23yvVM2ZWbrrpZb9PusVFin": DEXPlatform.SERUM,
            "SSwpkEEcbUqx4vtoEByFjSkhKdCT862DNVb52nZg1UZ": DEXPlatform.SABER,
            "MERLuDFBMmsHnsBPZw2sDQZHvXFMwp8EdjudcU2HKky": DEXPlatform.MERCURIAL,
            "AMM55ShdkoGRB5jVYPjWziwk8m5MpwyDgsMWHaMSQWH6": DEXPlatform.ALDRIN,
        }
        
        # SOL相关地址
        self.sol_addresses = {
            "native_sol": "11111111111111111111111111111111",
            "wrapped_sol": "So11111111111111111111111111111111111111112",
        }
        
        # 价格缓存
        self.price_cache = {}
        self.cache_expiry = {}
        
    async def analyze_transaction(self, transaction: SolanaTransaction) -> AnalysisResult:
        """
        分析单个交易
        
        Args:
            transaction: Solana交易对象
            
        Returns:
            分析结果
        """
        try:
            logger.debug(f"开始分析交易: {transaction.signature}")
            
            # 基础分析
            result = AnalysisResult(
                transaction=transaction,
                transaction_type=TransactionType.UNKNOWN
            )
            
            # 计算Gas费用
            if transaction.fee:
                result.gas_fee_sol = Decimal(transaction.fee) / Decimal(10**9)
                
            # 识别交易类型和平台
            await self._identify_transaction_type(result)
            
            # 根据类型进行详细分析
            if result.transaction_type == TransactionType.DEX_SWAP:
                await self._analyze_dex_swap(result)
            elif result.transaction_type in [TransactionType.SOL_TRANSFER, TransactionType.TOKEN_TRANSFER]:
                await self._analyze_transfer(result)
                
            # 计算总价值
            await self._calculate_total_value(result)
            
            # 风险评估
            self._assess_risk(result)
            
            logger.info(f"交易分析完成: {transaction.signature} - 类型: {result.transaction_type.value}")
            return result
            
        except Exception as e:
            logger.error(f"交易分析失败 {transaction.signature}: {str(e)}")
            return AnalysisResult(
                transaction=transaction,
                transaction_type=TransactionType.UNKNOWN,
                risk_level="high",
                risk_factors=["analysis_failed"]
            )
            
    async def _identify_transaction_type(self, result: AnalysisResult):
        """识别交易类型和DEX平台"""
        transaction = result.transaction
        
        # 检查程序交互
        for instruction in transaction.instructions:
            program_id = instruction.get('programId', '')
            
            # 识别DEX平台
            if program_id in self.known_programs:
                result.dex_platform = self.known_programs[program_id]
                result.transaction_type = TransactionType.DEX_SWAP
                return
                
        # 检查余额变化来推断交易类型
        if transaction.pre_balances and transaction.post_balances:
            balance_changes = []
            for i, (pre, post) in enumerate(zip(transaction.pre_balances, transaction.post_balances)):
                if pre != post:
                    balance_changes.append({
                        'account_index': i,
                        'pre_balance': pre,
                        'post_balance': post,
                        'change': post - pre
                    })
                    
            # 分析余额变化模式
            if len(balance_changes) == 2:
                # 可能是简单转账
                if any(change['change'] > 0 for change in balance_changes) and \
                   any(change['change'] < 0 for change in balance_changes):
                    result.transaction_type = TransactionType.SOL_TRANSFER
                    return
                    
        # 检查指令类型
        for instruction in transaction.instructions:
            instruction_data = instruction.get('parsed', {})
            if instruction_data.get('type') == 'transfer':
                result.transaction_type = TransactionType.SOL_TRANSFER
                return
                
        # 默认为程序交互
        if transaction.instructions:
            result.transaction_type = TransactionType.PROGRAM_INTERACTION
            
    async def _analyze_dex_swap(self, result: AnalysisResult):
        """分析DEX交换交易"""
        try:
            transaction = result.transaction
            
            # 这里需要根据不同DEX的指令格式来解析
            # 由于每个DEX的指令格式不同，这里提供一个通用的解析框架
            
            if result.dex_platform == DEXPlatform.RAYDIUM:
                await self._parse_raydium_swap(result)
            elif result.dex_platform == DEXPlatform.JUPITER:
                await self._parse_jupiter_swap(result)
            elif result.dex_platform == DEXPlatform.ORCA:
                await self._parse_orca_swap(result)
            else:
                await self._parse_generic_swap(result)
                
        except Exception as e:
            logger.error(f"DEX交换分析失败: {str(e)}")
            
    async def _parse_raydium_swap(self, result: AnalysisResult):
        """解析Raydium交换"""
        # Raydium特定的解析逻辑
        # 这里是示例实现，实际需要根据Raydium的具体指令格式
        logger.debug("解析Raydium交换")
        
    async def _parse_jupiter_swap(self, result: AnalysisResult):
        """解析Jupiter交换"""
        # Jupiter特定的解析逻辑
        logger.debug("解析Jupiter交换")
        
    async def _parse_orca_swap(self, result: AnalysisResult):
        """解析Orca交换"""
        # Orca特定的解析逻辑
        logger.debug("解析Orca交换")
        
    async def _parse_generic_swap(self, result: AnalysisResult):
        """通用交换解析"""
        transaction = result.transaction
        
        # 通过余额变化来推断交换信息
        if not transaction.pre_balances or not transaction.post_balances:
            return
            
        changes = []
        for i, (pre, post) in enumerate(zip(transaction.pre_balances, transaction.post_balances)):
            if pre != post and i < len(transaction.accounts):
                changes.append({
                    'address': transaction.accounts[i] if isinstance(transaction.accounts[i], str) else transaction.accounts[i].get('pubkey', ''),
                    'change': post - pre
                })
                
        # 找出输入和输出代币
        negative_changes = [c for c in changes if c['change'] < 0]
        positive_changes = [c for c in changes if c['change'] > 0]
        
        if len(negative_changes) >= 1 and len(positive_changes) >= 1:
            # 创建基础的交换信息
            from_token = TokenInfo(mint="unknown", symbol="UNKNOWN")
            to_token = TokenInfo(mint="unknown", symbol="UNKNOWN")
            
            result.swap_info = SwapInfo(
                from_token=from_token,
                to_token=to_token,
                from_amount=abs(Decimal(negative_changes[0]['change'])) / Decimal(10**9),
                to_amount=Decimal(positive_changes[0]['change']) / Decimal(10**9)
            )
            
    async def _analyze_transfer(self, result: AnalysisResult):
        """分析转账交易"""
        transaction = result.transaction
        
        if not transaction.pre_balances or not transaction.post_balances:
            return
            
        # 找到余额变化
        from_address = None
        to_address = None
        amount = Decimal('0')
        
        for i, (pre, post) in enumerate(zip(transaction.pre_balances, transaction.post_balances)):
            if pre != post and i < len(transaction.accounts):
                change = post - pre
                
                if change < 0:  # 发送方
                    from_address = transaction.accounts[i] if isinstance(transaction.accounts[i], str) else transaction.accounts[i].get('pubkey', '')
                    amount = abs(Decimal(change)) / Decimal(10**9)
                elif change > 0:  # 接收方
                    to_address = transaction.accounts[i] if isinstance(transaction.accounts[i], str) else transaction.accounts[i].get('pubkey', '')
                    
        # 创建转账信息
        if from_address and to_address:
            sol_token = TokenInfo(
                mint=self.sol_addresses["native_sol"],
                symbol="SOL",
                name="Solana",
                decimals=9
            )
            
            # 确定转账方向和对方地址（需要监控钱包地址）
            direction = None
            counterpart_address = None
            
            # 如果结果中包含钱包地址信息，则确定方向
            if hasattr(result, 'wallet_address') and result.wallet_address:
                direction, counterpart_address = self._determine_transfer_direction(transaction, result.wallet_address)
                logger.debug(f"转账分析 - 钱包: {result.wallet_address}, 方向: {direction}, 对方: {counterpart_address}")
            else:
                logger.warning(f"转账分析缺少钱包地址信息 - 签名: {transaction.signature}")
            
            result.transfer_info = TransferInfo(
                from_address=from_address,
                to_address=to_address,
                token=sol_token,
                amount=amount,
                direction=direction,
                counterpart_address=counterpart_address
            )

    async def _reanalyze_transfer_direction(self, result: AnalysisResult):
        """重新分析转账方向信息（当钱包地址在分析后才设置时）"""
        try:
            if not result.transfer_info or not hasattr(result, 'wallet_address'):
                return
                
            # 重新确定转账方向和对方地址
            direction, counterpart_address = self._determine_transfer_direction(
                result.transaction, 
                result.wallet_address
            )
            
            # 更新转账信息
            result.transfer_info.direction = direction
            result.transfer_info.counterpart_address = counterpart_address
            
            logger.debug(f"重新分析转账方向 - 钱包: {result.wallet_address}, 方向: {direction}, 对方: {counterpart_address}")
            
        except Exception as e:
            logger.error(f"重新分析转账方向失败: {e}")

    def _determine_transfer_direction(self, transaction, wallet_address: str) -> Tuple[Optional[str], Optional[str]]:
        """
        确定转账方向和对方地址
        
        Args:
            transaction: Solana交易对象
            wallet_address: 监控的钱包地址
            
        Returns:
            Tuple[direction, counterpart_address] 
            direction: 'in' (转入) 或 'out' (转出)
            counterpart_address: 对方钱包地址
        """
        try:
            if not transaction.pre_balances or not transaction.post_balances or not transaction.accounts:
                return None, None
            
            # 找到监控钱包在账户列表中的索引
            wallet_index = None
            for i, account in enumerate(transaction.accounts):
                account_address = account if isinstance(account, str) else account.get('pubkey', '')
                if account_address == wallet_address:
                    wallet_index = i
                    break
            
            if wallet_index is None:
                return None, None
            
            # 检查监控钱包的余额变化
            if wallet_index < len(transaction.pre_balances) and wallet_index < len(transaction.post_balances):
                pre_balance = transaction.pre_balances[wallet_index]
                post_balance = transaction.post_balances[wallet_index]
                balance_change = post_balance - pre_balance
                
                # 找到对方地址（余额变化相反的地址）
                counterpart_address = None
                for i, (pre, post) in enumerate(zip(transaction.pre_balances, transaction.post_balances)):
                    if i != wallet_index and i < len(transaction.accounts):
                        other_change = post - pre
                        
                        # 如果这个地址的余额变化与监控钱包相反，可能是对方
                        if (balance_change > 0 and other_change < 0) or (balance_change < 0 and other_change > 0):
                            account = transaction.accounts[i]
                            counterpart_address = account if isinstance(account, str) else account.get('pubkey', '')
                            
                            # 过滤掉系统程序地址和已知程序地址
                            if counterpart_address and not self._is_system_address(counterpart_address):
                                break
                
                # 确定方向
                if balance_change > 0:
                    return 'in', counterpart_address  # 转入
                elif balance_change < 0:
                    return 'out', counterpart_address  # 转出
                else:
                    return None, None  # 无余额变化
            
            return None, None
            
        except Exception as e:
            # 记录错误但不影响主流程
            import logging
            logging.warning(f"确定转账方向失败: {e}")
            return None, None

    def _is_system_address(self, address: str) -> bool:
        """
        判断是否为系统程序地址
        
        Args:
            address: 地址字符串
            
        Returns:
            bool: 是否为系统地址
        """
        system_addresses = {
            '11111111111111111111111111111111',  # System Program
            'TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA',  # Token Program
            'ATokenGPvbdGVxr1b2hvZbsiqW5xWH25efTNsLJA8knL',  # Associated Token Program
            'ComputeBudget111111111111111111111111111111',  # Compute Budget Program
            'SysvarRent111111111111111111111111111111111',  # Sysvar Rent
            'SysvarC1ock11111111111111111111111111111111',  # Sysvar Clock
        }
        
        # 检查是否为已知系统地址
        if address in system_addresses:
            return True
            
        # 检查是否为已知程序地址
        if hasattr(self, 'known_programs') and address in self.known_programs.values():
            return True
            
        return False
            
    async def _calculate_total_value(self, result: AnalysisResult):
        """计算交易总价值"""
        try:
            # 获取SOL价格
            sol_price = await self._get_token_price("SOL")
            
            # 计算Gas费用USD价值
            if result.gas_fee_sol and sol_price:
                result.gas_fee_usd = result.gas_fee_sol * sol_price
                
            # 计算交易价值
            if result.swap_info:
                # 交换交易
                if result.swap_info.from_token.symbol == "SOL" and sol_price:
                    result.swap_info.from_amount_usd = result.swap_info.from_amount * sol_price
                if result.swap_info.to_token.symbol == "SOL" and sol_price:
                    result.swap_info.to_amount_usd = result.swap_info.to_amount * sol_price
                    
                # 总价值取输入或输出的USD价值
                if result.swap_info.from_amount_usd:
                    result.total_value_usd = result.swap_info.from_amount_usd
                elif result.swap_info.to_amount_usd:
                    result.total_value_usd = result.swap_info.to_amount_usd
                    
            elif result.transfer_info:
                # 转账交易
                if result.transfer_info.token.symbol == "SOL" and sol_price:
                    result.transfer_info.amount_usd = result.transfer_info.amount * sol_price
                    result.total_value_usd = result.transfer_info.amount_usd
                    
        except Exception as e:
            logger.error(f"计算交易价值失败: {str(e)}")
            
    def _assess_risk(self, result: AnalysisResult):
        """风险评估"""
        risk_factors = []
        
        # 检查交易是否失败
        if not result.transaction.is_success:
            risk_factors.append("transaction_failed")
            
        # 检查大额交易
        if result.total_value_usd and result.total_value_usd > Decimal('10000'):
            risk_factors.append("large_amount")
            
        # 检查未知代币交换
        if result.swap_info:
            if result.swap_info.from_token.symbol == "UNKNOWN" or result.swap_info.to_token.symbol == "UNKNOWN":
                risk_factors.append("unknown_token")
                
        # 检查高滑点
        if result.swap_info and result.swap_info.price_impact and result.swap_info.price_impact > Decimal('0.05'):
            risk_factors.append("high_slippage")
            
        # 检查新代币
        # 这里可以添加代币创建时间检查
        
        # 确定风险级别
        if len(risk_factors) >= 3:
            result.risk_level = "high"
        elif len(risk_factors) >= 1:
            result.risk_level = "medium"
        else:
            result.risk_level = "low"
            
        result.risk_factors = risk_factors
        
    async def _get_token_price(self, symbol: str) -> Optional[Decimal]:
        """
        获取代币价格
        
        Args:
            symbol: 代币符号
            
        Returns:
            USD价格
        """
        try:
            # 简单的价格缓存机制
            current_time = datetime.now().timestamp()
            cache_key = symbol.upper()
            
            # 检查缓存
            if cache_key in self.price_cache and \
               cache_key in self.cache_expiry and \
               current_time < self.cache_expiry[cache_key]:
                return self.price_cache[cache_key]
                
            # 这里应该调用价格API获取实时价格
            # 为了示例，我们使用模拟价格
            mock_prices = {
                "SOL": Decimal("20.50"),
                "USDC": Decimal("1.00"),
                "USDT": Decimal("1.00"),
                "BTC": Decimal("43000.00"),
                "ETH": Decimal("2500.00")
            }
            
            price = mock_prices.get(symbol.upper())
            if price:
                # 缓存价格（5分钟）
                self.price_cache[cache_key] = price
                self.cache_expiry[cache_key] = current_time + 300
                
            return price
            
        except Exception as e:
            logger.error(f"获取代币价格失败 {symbol}: {str(e)}")
            return None
            
    async def get_token_info(self, mint_address: str) -> Optional[TokenInfo]:
        """
        获取代币信息
        
        Args:
            mint_address: 代币合约地址
            
        Returns:
            代币信息
        """
        try:
            # 已知代币映射
            known_tokens = {
                self.sol_addresses["native_sol"]: TokenInfo(
                    mint=self.sol_addresses["native_sol"],
                    symbol="SOL",
                    name="Solana",
                    decimals=9
                ),
                self.sol_addresses["wrapped_sol"]: TokenInfo(
                    mint=self.sol_addresses["wrapped_sol"],
                    symbol="SOL",
                    name="Wrapped Solana",
                    decimals=9
                ),
                "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v": TokenInfo(
                    mint="EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
                    symbol="USDC",
                    name="USD Coin",
                    decimals=6
                ),
                "Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB": TokenInfo(
                    mint="Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB",
                    symbol="USDT",
                    name="Tether USD",
                    decimals=6
                )
            }
            
            return known_tokens.get(mint_address)
            
        except Exception as e:
            logger.error(f"获取代币信息失败 {mint_address}: {str(e)}")
            return None
            
    def analyze_batch_transactions(self, transactions: List[SolanaTransaction]) -> List[AnalysisResult]:
        """
        批量分析交易
        
        Args:
            transactions: 交易列表
            
        Returns:
            分析结果列表
        """
        return asyncio.run(self._analyze_batch_async(transactions))
        
    async def _analyze_batch_async(self, transactions: List[SolanaTransaction]) -> List[AnalysisResult]:
        """异步批量分析"""
        tasks = [self.analyze_transaction(tx) for tx in transactions]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 处理异常结果
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"批量分析中交易 {i} 失败: {str(result)}")
                processed_results.append(AnalysisResult(
                    transaction=transactions[i],
                    transaction_type=TransactionType.UNKNOWN,
                    risk_level="high",
                    risk_factors=["analysis_error"]
                ))
            else:
                processed_results.append(result)
                
        return processed_results
        
    def get_summary_stats(self, results: List[AnalysisResult]) -> Dict[str, Any]:
        """
        获取分析结果统计
        
        Args:
            results: 分析结果列表
            
        Returns:
            统计信息
        """
        if not results:
            return {}
            
        total_transactions = len(results)
        successful_transactions = len([r for r in results if r.transaction.is_success])
        
        # 按类型统计
        type_counts = {}
        for result in results:
            type_name = result.transaction_type.value
            type_counts[type_name] = type_counts.get(type_name, 0) + 1
            
        # 按DEX平台统计
        dex_counts = {}
        for result in results:
            if result.dex_platform != DEXPlatform.UNKNOWN:
                dex_name = result.dex_platform.value
                dex_counts[dex_name] = dex_counts.get(dex_name, 0) + 1
                
        # 风险统计
        risk_counts = {}
        for result in results:
            risk_level = result.risk_level
            risk_counts[risk_level] = risk_counts.get(risk_level, 0) + 1
            
        # 价值统计
        total_values = [r.total_value_usd for r in results if r.total_value_usd]
        total_value_usd = sum(total_values) if total_values else Decimal('0')
        
        return {
            "total_transactions": total_transactions,
            "successful_transactions": successful_transactions,
            "success_rate": successful_transactions / total_transactions if total_transactions > 0 else 0,
            "transaction_types": type_counts,
            "dex_platforms": dex_counts,
            "risk_levels": risk_counts,
            "total_value_usd": float(total_value_usd),
            "average_value_usd": float(total_value_usd / len(total_values)) if total_values else 0
        }