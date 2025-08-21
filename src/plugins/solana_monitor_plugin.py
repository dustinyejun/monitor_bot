"""
Solana监控插件
将Solana钱包监控功能封装为可插拔的监控插件
"""

import asyncio
from datetime import datetime
from decimal import Decimal
from typing import Dict, Any, List

from ..core.monitor_plugin import MonitorPlugin
from ..services.notification_engine import notification_engine
from ..services.solana_analyzer import SolanaAnalyzer, TransactionType
from ..services.solana_client import SolanaClient
from ..services.solana_monitor import SolanaMonitorService
from ..utils.logger import logger


class SolanaMonitorPlugin(MonitorPlugin):
    """Solana监控插件"""

    def __init__(self, name: str, config: Dict[str, Any] = None):
        super().__init__(name, config)
        self.solana_client = None
        self.solana_analyzer = None
        self.solana_monitor = None

    @property
    def check_interval(self) -> int:
        """检查间隔（秒）"""
        return self.get_config("check_interval", 30)

    async def initialize(self) -> bool:
        """初始化Solana监控组件"""
        try:
            logger.info("初始化Solana监控插件...")

            # 获取RPC节点配置
            rpc_nodes = self.get_config("rpc_nodes", [])
            default_network = self.get_config("default_network", "mainnet")

            if not rpc_nodes:
                logger.error("Solana RPC节点未配置")
                return False

            # 初始化Solana客户端
            self.solana_client = SolanaClient(
                rpc_urls=rpc_nodes if isinstance(rpc_nodes, list) else None,
                network=default_network
            )

            # 测试RPC连接
            if not await self._test_rpc_connection():
                logger.error("Solana RPC连接测试失败")
                return False

            # 初始化分析器和监控服务
            self.solana_analyzer = SolanaAnalyzer()
            self.solana_monitor = SolanaMonitorService()

            logger.info("Solana监控插件初始化成功")
            return True

        except Exception as e:
            logger.error(f"Solana监控插件初始化失败: {str(e)}")
            return False

    async def _test_rpc_connection(self) -> bool:
        """测试RPC连接"""
        try:
            async with self.solana_client as client:
                health = await client.get_health()
                if health == "ok":
                    logger.info("Solana RPC连接测试成功")
                    return True
                else:
                    logger.warning(f"Solana RPC健康状态异常: {health}")
                    return False

        except Exception as e:
            logger.error(f"Solana RPC连接测试失败: {str(e)}")
            return False

    async def check(self) -> bool:
        """执行Solana监控检查"""
        try:
            logger.debug("执行Solana监控检查...")

            # 获取需要监控的钱包
            monitored_wallets = self.solana_monitor.get_active_wallets()
            if not monitored_wallets:
                logger.debug("没有需要监控的Solana钱包")
                return True

            check_success = True
            processed_count = 0

            async with self.solana_client as client:
                for wallet in monitored_wallets:
                    try:
                        logger.debug(
                            f"检查钱包 {wallet.address[:8]}... (last_signature: {wallet.last_signature[:16] if wallet.last_signature else 'None'}...)")

                        # 获取钱包最新交易
                        signatures = await client.get_signatures_for_address(
                            wallet.address,
                            limit=50,  # 增加限制以便过滤
                            until=wallet.last_signature  # 修复：获取last_signature之后的新交易
                        )

                        if signatures:
                            # 过滤只获取当天的交易
                            today_signatures = self._filter_today_signatures(signatures)
                            logger.debug(
                                f"钱包 {wallet.address[:8]}... 获取到 {len(signatures)} 笔交易，当天交易 {len(today_signatures)} 笔")

                            # 由于使用after参数，today_signatures已经都是新交易，无需额外过滤
                            new_signatures = today_signatures
                            logger.debug(f"钱包 {wallet.address[:8]}... 当天新交易 {len(new_signatures)} 笔")

                            if new_signatures:
                                # 分析交易
                                analyzed_transactions = []
                                for signature_obj in new_signatures:
                                    try:
                                        # 提取签名字符串
                                        signature_str = self._extract_signature_string(signature_obj)

                                        if signature_str:
                                            # **关键修复：检查交易是否已经在数据库中处理过**
                                            if self.solana_monitor.is_transaction_processed(signature_str):
                                                logger.debug(f"跳过已处理交易: {signature_str[:16]}...")
                                                continue

                                            tx = await client.get_transaction(signature_str)
                                            if tx:
                                                analysis = await self.solana_analyzer.analyze_transaction(tx)
                                                # 确保分析结果包含钱包地址
                                                if not hasattr(analysis, 'wallet_address'):
                                                    analysis.wallet_address = wallet.address
                                                analyzed_transactions.append(analysis)
                                                logger.debug(f"分析交易成功: {signature_str[:16]}...")
                                        else:
                                            logger.warning(f"无法提取签名字符串: {signature_obj}")
                                    except Exception as e:
                                        logger.warning(f"分析交易 {signature_obj} 失败: {str(e)}")
                                        continue

                                # 处理分析结果
                                if analyzed_transactions:
                                    await self._process_analyzed_transactions(wallet, analyzed_transactions)
                                    processed_count += len(analyzed_transactions)

                        # 更新检查时间和最后签名
                        if signatures:
                            # 提取最新签名字符串（从签名对象中）
                            latest_signature = self._extract_signature_string(signatures[0])

                            if latest_signature:
                                self.solana_monitor.update_wallet_check_info(
                                    wallet.address,
                                    latest_signature,
                                    datetime.now()
                                )
                                logger.info(f"✅ 更新钱包 {wallet.address[:8]}... 最新签名: {latest_signature[:16]}...")
                            else:
                                logger.warning(f"无法提取签名字符串: {signatures[0]}")
                                self.solana_monitor.update_wallet_check_time(
                                    wallet.address,
                                    datetime.now()
                                )
                        else:
                            self.solana_monitor.update_wallet_check_time(
                                wallet.address,
                                datetime.now()
                            )
                            logger.debug(f"钱包 {wallet.address[:8]}... 无新交易")

                    except Exception as e:
                        logger.error(f"检查钱包 {wallet.address} 失败: {str(e)}")
                        check_success = False
                        continue

            logger.info(f"Solana监控检查完成，处理了 {processed_count} 笔交易")
            return check_success

        except Exception as e:
            logger.error(f"Solana监控检查失败: {str(e)}")
            return False

    async def _process_analyzed_transactions(self, wallet, analyzed_transactions: List[Any]):
        """处理分析后的交易"""
        try:
            # 按区块时间排序（从早到晚）
            analyzed_transactions.sort(key=lambda tx: getattr(tx.transaction, 'block_time', 0) or 0)

            # 筛选重要交易
            important_transactions = []

            for analysis in analyzed_transactions:
                # 筛选条件：
                # 1. 大额交易 (>1000 USD)
                # 2. DEX交换交易
                # 3. 新代币交易
                if (self._is_important_transaction(analysis, wallet)):
                    important_transactions.append(analysis)

            if important_transactions:
                logger.info(f"发现 {len(important_transactions)} 笔重要交易")

                # 保存到数据库（按时间顺序）
                for analysis in important_transactions:
                    # 确保分析结果包含钱包地址
                    if not hasattr(analysis, 'wallet_address'):
                        analysis.wallet_address = wallet.address
                    await self.solana_monitor.save_transaction_analysis(analysis)

                # 按时间顺序触发通知（确保早的交易先通知）
                await self._trigger_notifications_in_order(wallet, important_transactions)

        except Exception as e:
            logger.error(f"处理分析交易失败: {str(e)}")

    async def _trigger_notifications_in_order(self, wallet, important_transactions: List[Any]):
        """按时间顺序触发通知，确保早的交易先通知"""
        try:
            logger.info(f"开始按时间顺序发送 {len(important_transactions)} 笔交易通知")

            for i, analysis in enumerate(important_transactions):
                try:
                    block_time = getattr(analysis.transaction, 'block_time', None)
                    logger.debug(f"发送第 {i + 1} 笔交易通知，区块时间: {block_time}")

                    # 发送单笔交易通知
                    await self._trigger_single_notification(wallet, analysis)

                    # 添加小延迟确保通知顺序（可选）
                    await asyncio.sleep(0.1)

                except Exception as e:
                    logger.error(f"发送第 {i + 1} 笔交易通知失败: {str(e)}")
                    continue

        except Exception as e:
            logger.error(f"按顺序触发通知失败: {str(e)}")

    async def _trigger_single_notification(self, wallet, analysis):
        """触发单笔交易的通知"""
        try:
            # 从交易分析结果中提取金额和代币信息
            amount = 0
            token_symbol = "SOL"
            token_name = "Solana"

            if analysis.transfer_info:
                amount = float(analysis.transfer_info.amount)
                token_symbol = analysis.transfer_info.token.symbol or "SOL"
                token_name = analysis.transfer_info.token.name or "Solana"
            elif analysis.swap_info:
                # 对于交换，使用接收到的代币信息
                amount = float(analysis.swap_info.to_amount)
                token_symbol = analysis.swap_info.to_token.symbol or "UNKNOWN"
                token_name = analysis.swap_info.to_token.name or "Unknown Token"

            # 获取区块时间
            block_time = "未知"
            if hasattr(analysis.transaction, 'block_time') and analysis.transaction.block_time:
                block_time = datetime.fromtimestamp(analysis.transaction.block_time).strftime('%Y-%m-%d %H:%M:%S')

            # 构建通知数据 - 保持与原来格式一致
            notification_data = {
                "wallet_address": wallet.address,
                "wallet_alias": wallet.alias or wallet.address[:8] + "...",
                "transaction_type": analysis.transaction_type.value,
                "signature": analysis.transaction.signature,
                "amount": amount,  # 保持数字格式
                "amount_usd": float(analysis.total_value_usd) if analysis.total_value_usd else 0,
                "token_symbol": token_symbol,
                "token_name": token_name,
                "solscan_url": f"https://solscan.io/tx/{analysis.transaction.signature}",
                "block_time": block_time
            }

            # 调试日志
            logger.debug(
                f"准备发送通知 - 交易类型: {notification_data['transaction_type']}, 美元价值: ${notification_data['amount_usd']}")

            # 发送通知 - 使用已导入的notification_engine
            await notification_engine.check_solana_rules(notification_data)

            logger.info(f"发现重要交易: {wallet.address} - "
                        f"{analysis.transaction_type.value} - "
                        f"${analysis.total_value_usd}")

        except Exception as e:
            logger.error(f"触发单笔通知失败: {str(e)}")

    def _is_important_transaction(self, analysis, wallet) -> bool:
        """判断是否为重要交易"""
        try:
            # 根据交易类型进行不同的判断逻辑
            transaction_type = analysis.transaction_type

            # SOL转账交易
            if transaction_type == TransactionType.SOL_TRANSFER:
                return self._check_sol_transfer(analysis, wallet)

            # 代币转账交易
            elif transaction_type == TransactionType.TOKEN_TRANSFER:
                return self._check_token_transfer(analysis, wallet)

            # DEX交换交易
            elif transaction_type == TransactionType.DEX_SWAP:
                return self._check_dex_swap(analysis, wallet)

            # DEX添加流动性
            elif transaction_type == TransactionType.DEX_ADD_LIQUIDITY:
                return self._check_dex_add_liquidity(analysis, wallet)

            # DEX移除流动性
            elif transaction_type == TransactionType.DEX_REMOVE_LIQUIDITY:
                return self._check_dex_remove_liquidity(analysis, wallet)

            # 代币铸造
            elif transaction_type == TransactionType.TOKEN_MINT:
                return self._check_token_mint(analysis, wallet)

            # 代币销毁
            elif transaction_type == TransactionType.TOKEN_BURN:
                return self._check_token_burn(analysis, wallet)

            # 程序交互
            elif transaction_type == TransactionType.PROGRAM_INTERACTION:
                return self._check_program_interaction(analysis, wallet)

            # 未知类型，使用通用逻辑
            else:
                return False

        except Exception as e:
            logger.warning(f"判断交易重要性失败: {str(e)}")
            return False

    def _check_sol_transfer(self, analysis, wallet) -> bool:
        """检查SOL转账交易"""
        try:
            from ..config.settings import settings

            # 获取配置的SOL转账监控金额阈值
            min_amount = Decimal(str(settings.sol_transfer_amount))
            
            # 检查转账的SOL金额
            if analysis.transfer_info and analysis.transfer_info.amount:
                sol_amount = float(analysis.transfer_info.amount)
                if sol_amount >= min_amount:
                    return True
            
            return False

        except Exception as e:
            logger.warning(f"检查SOL转账失败: {str(e)}")
            return False

    def _check_token_transfer(self, analysis, wallet) -> bool:
        """检查代币转账交易"""
        try:
            from ..config.settings import settings

            # 使用配置的代币转账监控金额阈值
            min_amount = Decimal(str(settings.token_transfer_amount))
            
            # 检查转账的代币金额
            if analysis.transfer_info and analysis.transfer_info.amount:
                token_amount = float(analysis.transfer_info.amount)
                if token_amount >= min_amount:
                    return True
            
            return False

        except Exception as e:
            logger.warning(f"检查代币转账失败: {str(e)}")
            return False

    def _check_dex_swap(self, analysis, wallet) -> bool:
        """检查DEX交换交易"""
        try:
            from ..config.settings import settings

            # 使用配置的DEX交换监控金额阈值
            min_amount = Decimal(str(settings.dex_swap_amount))
            
            # 检查DEX交换的金额
            if analysis.swap_info:
                def is_sol_token(token):
                    """检查代币是否为SOL"""
                    return token and (
                        token.symbol == "SOL" or 
                        token.mint == "So11111111111111111111111111111111111111112"
                    )
                
                # SOL -> 其他代币：检查from_amount（SOL数量）
                if (is_sol_token(analysis.swap_info.from_token) and 
                    analysis.swap_info.from_amount):
                    sol_amount = float(analysis.swap_info.from_amount)
                    if sol_amount >= min_amount:
                        return True
                
                # 其他代币 -> SOL：检查to_amount（SOL数量）
                if (is_sol_token(analysis.swap_info.to_token) and 
                    analysis.swap_info.to_amount):
                    sol_amount = float(analysis.swap_info.to_amount)
                    if sol_amount >= min_amount:
                        return True
            
            return False

        except Exception as e:
            logger.warning(f"检查DEX交换失败: {str(e)}")
            return False

    def _check_dex_add_liquidity(self, analysis, wallet) -> bool:
        """检查DEX添加流动性交易"""
        try:
            from ..config.settings import settings

            # 使用配置的DEX添加流动性监控金额阈值
            min_amount = Decimal(str(settings.dex_add_liquidity_amount))
            return True

        except Exception as e:
            logger.warning(f"检查添加流动性失败: {str(e)}")
            return False

    def _check_dex_remove_liquidity(self, analysis, wallet) -> bool:
        """检查DEX移除流动性交易"""
        try:
            from ..config.settings import settings

            # 使用配置的DEX移除流动性监控金额阈值
            min_amount = Decimal(str(settings.dex_remove_liquidity_amount))
            return True

        except Exception as e:
            logger.warning(f"检查移除流动性失败: {str(e)}")
            return False

    def _check_token_mint(self, analysis, wallet) -> bool:
        """检查代币铸造交易"""
        try:
            return False

        except Exception as e:
            logger.warning(f"检查代币铸造失败: {str(e)}")
            return False

    def _check_token_burn(self, analysis, wallet) -> bool:
        """检查代币销毁交易"""
        try:
            return True
        except Exception as e:
            logger.warning(f"检查代币销毁失败: {str(e)}")
            return False

    def _check_program_interaction(self, analysis, wallet) -> bool:
        """检查程序交互交易"""
        try:
            return False
        except Exception as e:
            logger.warning(f"检查程序交互失败: {str(e)}")
            return False

    def _check_generic_transaction(self, analysis, wallet) -> bool:
        """检查通用交易（兜底逻辑）"""
        try:
            return False
        except Exception as e:
            logger.warning(f"检查通用交易失败: {str(e)}")
            return False

    def _filter_today_signatures(self, signatures: List[str]) -> List[str]:
        """过滤出当天的交易签名"""
        if not signatures:
            return []

        try:
            today = datetime.now().date()
            today_signatures = []

            for signature in signatures:
                try:
                    # 从签名信息中获取区块时间
                    # signatures 是从 get_signatures_for_address 返回的，每个元素包含 blockTime
                    if hasattr(signature, 'blockTime') and signature.blockTime:
                        block_time = datetime.fromtimestamp(signature.blockTime).date()
                        if block_time == today:
                            today_signatures.append(signature)
                    elif isinstance(signature, dict) and 'blockTime' in signature:
                        block_time = datetime.fromtimestamp(signature['blockTime']).date()
                        if block_time == today:
                            today_signatures.append(signature)
                    else:
                        # 如果没有时间信息，保守起见包含在内
                        today_signatures.append(signature)
                except Exception as e:
                    logger.warning(f"过滤签名 {signature} 时间失败: {str(e)}")
                    # 如果解析失败，保守起见包含在内
                    today_signatures.append(signature)

            logger.debug(f"从 {len(signatures)} 个签名中过滤出当天的 {len(today_signatures)} 个")
            return today_signatures

        except Exception as e:
            logger.error(f"过滤当天签名失败: {str(e)}")
            # 如果过滤失败，返回所有签名
            return signatures

    def _filter_new_signatures(self, signatures, last_signature: str):
        """
        过滤出新的签名（排除已经处理过的签名）
        
        Args:
            signatures: 签名列表
            last_signature: 上次处理的最后一个签名
            
        Returns:
            新的签名列表（排除last_signature及其之前的签名）
        """
        if not signatures or not last_signature:
            return signatures

        try:
            new_signatures = []

            for signature_obj in signatures:
                signature_str = self._extract_signature_string(signature_obj)

                # 如果找到了last_signature，停止添加（因为这个及之后的都是已处理的）
                if signature_str == last_signature:
                    logger.debug(f"找到last_signature {last_signature[:16]}...，停止收集新签名")
                    break

                # 这是新的签名，添加到列表
                new_signatures.append(signature_obj)

            logger.debug(f"从 {len(signatures)} 个签名中过滤出 {len(new_signatures)} 个新签名")
            return new_signatures

        except Exception as e:
            logger.error(f"过滤新签名失败: {str(e)}")
            # 如果过滤失败，为安全起见返回空列表，避免重复处理
            return []

    def _extract_signature_string(self, signature_obj):
        """
        从签名对象中提取签名字符串
        
        Args:
            signature_obj: 签名对象（可能是字典、对象或字符串）
            
        Returns:
            签名字符串，如果提取失败返回None
        """
        try:
            if isinstance(signature_obj, dict) and 'signature' in signature_obj:
                return signature_obj['signature']
            elif hasattr(signature_obj, 'signature'):
                return signature_obj.signature
            elif isinstance(signature_obj, str):
                return signature_obj
            else:
                return None
        except Exception as e:
            logger.warning(f"提取签名字符串失败: {str(e)}")
            return None

    async def _trigger_notifications(self, wallet, important_transactions: List[Any]):
        """触发通知"""
        try:
            for analysis in important_transactions:
                # 准备通知数据
                signature = analysis.transaction.signature

                # 从交易分析结果中提取金额和代币信息
                amount = 0
                token_symbol = "SOL"
                token_name = "Solana"

                if analysis.transfer_info:
                    amount = float(analysis.transfer_info.amount)
                    token_symbol = analysis.transfer_info.token.symbol or "SOL"
                    token_name = analysis.transfer_info.token.name or "Solana"
                elif analysis.swap_info:
                    # 对于交换，使用接收到的代币信息
                    amount = float(analysis.swap_info.to_amount)
                    token_symbol = analysis.swap_info.to_token.symbol or "UNKNOWN"
                    token_name = analysis.swap_info.to_token.name or "Unknown Token"

                # 获取区块时间
                block_time = "未知"
                if hasattr(analysis.transaction, 'block_time') and analysis.transaction.block_time:
                    from datetime import datetime
                    block_time = datetime.fromtimestamp(analysis.transaction.block_time).strftime('%Y-%m-%d %H:%M:%S')

                notification_data = {
                    "wallet_address": wallet.address,
                    "wallet_alias": wallet.alias or wallet.address[:8] + "...",
                    "transaction_type": analysis.transaction_type.value,
                    "signature": signature,
                    "amount": amount,
                    "amount_usd": float(analysis.total_value_usd) if analysis.total_value_usd else 0,
                    "token_symbol": token_symbol,
                    "token_name": token_name,
                    "solscan_url": f"https://solscan.io/tx/{signature}",
                    "block_time": block_time
                }

                # 触发通知引擎检查规则
                await notification_engine.check_solana_rules(notification_data)

                logger.info(f"发现重要交易: {wallet.address} - "
                            f"{analysis.transaction_type.value} - "
                            f"${analysis.total_value_usd}")

        except Exception as e:
            logger.error(f"触发通知失败: {str(e)}")

    async def cleanup(self):
        """清理资源"""
        try:
            logger.info("清理Solana监控插件资源...")

            if self.solana_client:
                # Solana客户端使用上下文管理器，无需特殊清理
                pass

            self.solana_client = None
            self.solana_analyzer = None
            self.solana_monitor = None

            logger.info("Solana监控插件资源清理完成")

        except Exception as e:
            logger.error(f"Solana监控插件清理失败: {str(e)}")

    async def get_wallet_balance(self, address: str) -> Dict[str, Any]:
        """获取钱包余额（插件特有功能）"""
        try:
            async with self.solana_client as client:
                # SOL余额
                sol_balance = await client.get_balance(address)

                # 代币余额
                token_accounts = await client.get_token_accounts(address)

                return {
                    "address": address,
                    "sol_balance": sol_balance / 10 ** 9,  # 转换为SOL
                    "token_count": len(token_accounts),
                    "tokens": [
                        {
                            "mint": token.mint,
                            "balance": float(token.balance),
                            "decimals": token.decimals
                        }
                        for token in token_accounts
                    ]
                }

        except Exception as e:
            logger.error(f"获取钱包余额失败 {address}: {str(e)}")
            return {"error": str(e)}

    def get_plugin_info(self) -> Dict[str, Any]:
        """获取插件信息"""
        rpc_info = {}
        if self.solana_client:
            rpc_info = self.solana_client.get_connection_info()

        return {
            "name": self.name,
            "type": "solana_monitor",
            "version": "1.0.0",
            "description": "监控Solana钱包交易，识别大额转账和DEX交换",
            "config": {
                "check_interval": self.check_interval,
                "network": self.get_config("default_network", "mainnet"),
                "rpc_nodes_count": len(self.get_config("rpc_nodes", [])),
            },
            "rpc_status": rpc_info,
            "stats": {
                "status": self.stats.status.value,
                "total_checks": self.stats.total_checks,
                "success_rate": self.stats.success_rate,
                "uptime_seconds": self.stats.uptime_seconds,
            }
        }


# 注册插件
from ..core.monitor_plugin import plugin_registry

plugin_registry.register("solana", SolanaMonitorPlugin)
