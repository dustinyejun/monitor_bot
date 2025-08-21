"""
Solana RPC客户端
负责与Solana区块链进行交互，查询钱包余额、交易记录等信息
"""

import asyncio
import aiohttp
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, field
import base58
import json
from datetime import datetime, timezone
from decimal import Decimal

from ..config.settings import settings
from ..utils.logger import logger


@dataclass
class SolanaTokenInfo:
    """Solana代币信息"""
    mint: str
    amount: int
    decimals: int
    ui_amount: Optional[float] = None
    ui_amount_string: Optional[str] = None
    token_program: Optional[str] = None
    
    @property
    def balance(self) -> Decimal:
        """获取代币余额（考虑精度）"""
        return Decimal(self.amount) / (Decimal(10) ** self.decimals)


@dataclass
class SolanaAccountInfo:
    """Solana账户信息"""
    address: str
    lamports: int
    owner: str
    executable: bool
    rent_epoch: int
    tokens: List[SolanaTokenInfo] = field(default_factory=list)
    
    @property
    def sol_balance(self) -> Decimal:
        """SOL余额（以SOL为单位）"""
        return Decimal(self.lamports) / Decimal(10**9)


@dataclass
class SolanaTransaction:
    """Solana交易信息"""
    signature: str
    slot: int
    block_time: Optional[int] = None
    confirmations: Optional[int] = None
    err: Optional[Dict] = None
    memo: Optional[str] = None
    fee: Optional[int] = None
    
    # 交易详细信息
    accounts: List[str] = field(default_factory=list)
    instructions: List[Dict] = field(default_factory=list)
    pre_balances: List[int] = field(default_factory=list)
    post_balances: List[int] = field(default_factory=list)
    
    @property
    def datetime(self) -> Optional[datetime]:
        """交易时间戳转换为datetime"""
        if self.block_time:
            return datetime.fromtimestamp(self.block_time, tz=timezone.utc)
        return None
    
    @property
    def is_success(self) -> bool:
        """交易是否成功"""
        return self.err is None


class SolanaRPCError(Exception):
    """Solana RPC异常"""
    def __init__(self, message: str, code: int = None, data: Any = None):
        self.message = message
        self.code = code
        self.data = data
        super().__init__(self.message)


class SolanaClient:
    """Solana RPC客户端 - 支持多节点备份和自动切换"""
    
    def __init__(self, rpc_urls: List[str] = None, network: str = None):
        """
        初始化Solana客户端
        
        Args:
            rpc_urls: RPC节点URL列表，如果为None则从配置获取
            network: 网络类型 (mainnet, devnet, testnet)，如果为None则使用默认网络
        """
        if rpc_urls:
            self.rpc_urls = rpc_urls
            self.network = "custom"
        else:
            self.network = network or settings.solana_default_network
            self.rpc_urls = settings.get_rpc_nodes_by_network(self.network)
            
        if not self.rpc_urls:
            raise ValueError(f"没有可用的RPC节点配置 (网络: {self.network})")
            
        self.current_url_index = 0
        self.current_url = self.rpc_urls[0]
        self.session = None
        self._request_id = 0
        self.failed_nodes = set()  # 记录失败的节点
        self.last_health_check = 0  # 上次健康检查时间
        
    async def __aenter__(self):
        """异步上下文管理器入口"""
        timeout = aiohttp.ClientTimeout(
            total=settings.solana_rpc_timeout,
            connect=10
        )
        
        self.session = aiohttp.ClientSession(
            timeout=timeout,
            headers={
                "Content-Type": "application/json",
                "User-Agent": "MonitorBot/1.0"
            }
        )
        
        # 执行初始健康检查
        await self._perform_health_check()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器退出"""
        if self.session:
            await self.session.close()
            
    def _get_request_id(self) -> int:
        """获取请求ID"""
        self._request_id += 1
        return self._request_id
        
    async def _perform_health_check(self) -> bool:
        """
        执行健康检查，找到可用的RPC节点
        
        Returns:
            是否找到可用节点
        """
        import time
        current_time = time.time()
        
        # 如果距离上次检查时间不足，跳过检查
        if current_time - self.last_health_check < settings.solana_rpc_health_check_interval:
            return True
            
        logger.info("开始RPC节点健康检查...")
        
        for i, url in enumerate(self.rpc_urls):
            if url in self.failed_nodes:
                continue
                
            try:
                # 简单的健康检查请求
                request_payload = {
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "getHealth"
                }
                
                async with self.session.post(url, json=request_payload) as response:
                    if response.status == 200:
                        result = await response.json()
                        if 'result' in result or result.get('result') == 'ok':
                            self.current_url_index = i
                            self.current_url = url
                            self.last_health_check = current_time
                            logger.info(f"选择RPC节点: {url}")
                            return True
                            
            except Exception as e:
                logger.warning(f"RPC节点不可用: {url} - {str(e)}")
                self.failed_nodes.add(url)
                continue
                
        # 如果所有节点都失败，清除失败记录并重试第一个
        if len(self.failed_nodes) >= len(self.rpc_urls):
            logger.warning("所有RPC节点都失败，重置失败记录")
            self.failed_nodes.clear()
            self.current_url_index = 0
            self.current_url = self.rpc_urls[0]
            
        return False
        
    async def _switch_to_next_node(self) -> bool:
        """
        切换到下一个可用节点
        
        Returns:
            是否成功切换
        """
        logger.warning(f"当前节点失败，尝试切换: {self.current_url}")
        self.failed_nodes.add(self.current_url)
        
        # 尝试下一个节点
        for i in range(len(self.rpc_urls)):
            next_index = (self.current_url_index + 1 + i) % len(self.rpc_urls)
            next_url = self.rpc_urls[next_index]
            
            if next_url not in self.failed_nodes:
                self.current_url_index = next_index
                self.current_url = next_url
                logger.info(f"切换到新节点: {next_url}")
                return True
                
        logger.error("没有可用的RPC节点")
        return False
        
    async def _make_rpc_request(
        self, 
        method: str, 
        params: List[Any] = None,
        retries: int = 3
    ) -> Any:
        """
        发送RPC请求
        
        Args:
            method: RPC方法名
            params: 请求参数
            retries: 重试次数
            
        Returns:
            RPC响应结果
            
        Raises:
            SolanaRPCError: RPC请求失败
        """
        if not self.session:
            raise SolanaRPCError("SolanaClient未初始化，请使用async with语句")
            
        request_payload = {
            "jsonrpc": "2.0",
            "id": self._get_request_id(),
            "method": method,
            "params": params or []
        }
        
        for attempt in range(retries + 1):
            try:
                logger.debug(f"Solana RPC请求: {method} -> {self.current_url}")
                
                async with self.session.post(
                    self.current_url,
                    json=request_payload
                ) as response:
                    
                    if response.status != 200:
                        raise SolanaRPCError(
                            f"HTTP错误: {response.status}",
                            code=response.status
                        )
                        
                    response_data = await response.json()
                    logger.info(f"RPC响应: {method} - 状态: {response.status}")
                    
                    # 检查RPC错误
                    if 'error' in response_data:
                        error = response_data['error']
                        raise SolanaRPCError(
                            f"RPC错误: {error.get('message', '未知错误')}",
                            code=error.get('code'),
                            data=error.get('data')
                        )
                        
                    return response_data.get('result')
                    
            except asyncio.TimeoutError:
                if attempt < retries:
                    # 尝试切换节点
                    if await self._switch_to_next_node():
                        logger.info("节点切换成功，继续重试")
                        continue
                    
                    wait_time = 2 ** attempt
                    logger.warning(f"RPC请求超时，{wait_time}秒后重试 (第{attempt + 1}次)")
                    await asyncio.sleep(wait_time)
                    continue
                else:
                    raise SolanaRPCError("RPC请求超时，已达最大重试次数")
                    
            except aiohttp.ClientError as e:
                if attempt < retries:
                    # 尝试切换节点
                    if await self._switch_to_next_node():
                        logger.info("节点切换成功，继续重试")
                        continue
                        
                    wait_time = 2 ** attempt
                    logger.warning(f"网络错误，{wait_time}秒后重试: {str(e)}")
                    await asyncio.sleep(wait_time)
                    continue
                else:
                    raise SolanaRPCError(f"网络请求失败: {str(e)}")
                    
            except json.JSONDecodeError as e:
                raise SolanaRPCError(f"JSON解析错误: {str(e)}")
                
        raise SolanaRPCError("所有重试均失败")
        
    async def get_health(self) -> str:
        """
        检查RPC节点健康状态
        
        Returns:
            健康状态字符串
        """
        try:
            result = await self._make_rpc_request("getHealth")
            return "ok" if result == "ok" else str(result)
        except SolanaRPCError:
            return "unhealthy"
            
    async def get_version(self) -> Dict[str, Any]:
        """
        获取节点版本信息
        
        Returns:
            版本信息
        """
        return await self._make_rpc_request("getVersion")
        
    async def get_balance(self, address: str) -> int:
        """
        获取账户SOL余额
        
        Args:
            address: 账户地址
            
        Returns:
            余额（lamports）
        """
        try:
            # 验证地址格式
            self._validate_address(address)
            
            result = await self._make_rpc_request(
                "getBalance",
                [address]
            )
            
            return result.get('value', 0)
            
        except Exception as e:
            logger.error(f"获取余额失败 {address}: {str(e)}")
            raise SolanaRPCError(f"获取余额失败: {str(e)}")
            
    async def get_account_info(self, address: str) -> Optional[SolanaAccountInfo]:
        """
        获取账户详细信息
        
        Args:
            address: 账户地址
            
        Returns:
            账户信息
        """
        try:
            self._validate_address(address)
            
            result = await self._make_rpc_request(
                "getAccountInfo",
                [
                    address,
                    {
                        "encoding": "jsonParsed",
                        "commitment": "confirmed"
                    }
                ]
            )
            
            if not result or not result.get('value'):
                logger.warning(f"账户不存在或无数据: {address}")
                return None
                
            account_data = result['value']
            
            return SolanaAccountInfo(
                address=address,
                lamports=account_data.get('lamports', 0),
                owner=account_data.get('owner', ''),
                executable=account_data.get('executable', False),
                rent_epoch=account_data.get('rentEpoch', 0)
            )
            
        except Exception as e:
            logger.error(f"获取账户信息失败 {address}: {str(e)}")
            raise SolanaRPCError(f"获取账户信息失败: {str(e)}")
            
    async def get_token_accounts(self, address: str) -> List[SolanaTokenInfo]:
        """
        获取账户的代币账户信息
        
        Args:
            address: 钱包地址
            
        Returns:
            代币账户列表
        """
        try:
            self._validate_address(address)
            
            result = await self._make_rpc_request(
                "getTokenAccountsByOwner",
                [
                    address,
                    {"programId": "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"},  # SPL Token Program
                    {
                        "encoding": "jsonParsed",
                        "commitment": "confirmed"
                    }
                ]
            )
            
            tokens = []
            if result and result.get('value'):
                for token_account in result['value']:
                    account_info = token_account.get('account', {})
                    parsed_info = account_info.get('data', {}).get('parsed', {}).get('info', {})
                    
                    if parsed_info:
                        token_amount = parsed_info.get('tokenAmount', {})
                        tokens.append(SolanaTokenInfo(
                            mint=parsed_info.get('mint', ''),
                            amount=int(token_amount.get('amount', 0)),
                            decimals=token_amount.get('decimals', 0),
                            ui_amount=token_amount.get('uiAmount'),
                            ui_amount_string=token_amount.get('uiAmountString')
                        ))
                        
            logger.info(f"获取到 {len(tokens)} 个代币账户: {address}")
            return tokens
            
        except Exception as e:
            logger.error(f"获取代币账户失败 {address}: {str(e)}")
            raise SolanaRPCError(f"获取代币账户失败: {str(e)}")
            
    async def get_signatures_for_address(
        self, 
        address: str, 
        limit: int = 10,
        before: str = None,
        until: str = None
    ) -> List[str]:
        """
        获取地址相关的交易签名列表
        
        Args:
            address: 账户地址
            limit: 返回数量限制
            before: 在此签名之前的交易
            until: 在此签名之后的交易
            
        Returns:
            交易签名列表
        """
        try:
            self._validate_address(address)
            
            params = [
                address,
                {
                    "limit": min(limit, 1000),  # 限制最大1000条
                    "commitment": "confirmed"
                }
            ]
            
            if before:
                params[1]["before"] = before
            if until:
                params[1]["until"] = until
                
            result = await self._make_rpc_request(
                "getSignaturesForAddress",
                params
            )
            
            signatures = []
            if result:
                signatures = [tx.get('signature', '') for tx in result if tx.get('signature')]
                
            logger.info(f"获取到 {len(signatures)} 个交易签名: {address}")
            return signatures
            
        except Exception as e:
            logger.error(f"获取交易签名失败 {address}: {str(e)}")
            raise SolanaRPCError(f"获取交易签名失败: {str(e)}")
            
    async def get_transaction(self, signature: str) -> Optional[SolanaTransaction]:
        """
        获取交易详细信息
        
        Args:
            signature: 交易签名
            
        Returns:
            交易信息
        """
        try:
            result = await self._make_rpc_request(
                "getTransaction",
                [
                    signature,
                    {
                        "encoding": "jsonParsed",
                        "commitment": "confirmed",
                        "maxSupportedTransactionVersion": 0
                    }
                ]
            )
            
            if not result:
                logger.warning(f"交易不存在: {signature}")
                return None
                
            # 解析交易数据
            meta = result.get('meta', {})
            transaction = result.get('transaction', {})
            message = transaction.get('message', {})
            
            return SolanaTransaction(
                signature=signature,
                slot=result.get('slot', 0),
                block_time=result.get('blockTime'),
                confirmations=meta.get('confirmations'),
                err=meta.get('err'),
                fee=meta.get('fee'),
                accounts=message.get('accountKeys', []),
                instructions=message.get('instructions', []),
                pre_balances=meta.get('preBalances', []),
                post_balances=meta.get('postBalances', [])
            )
            
        except Exception as e:
            logger.error(f"获取交易信息失败 {signature}: {str(e)}")
            raise SolanaRPCError(f"获取交易信息失败: {str(e)}")
            
    async def get_recent_performance_samples(self, limit: int = 5) -> List[Dict]:
        """
        获取近期性能样本
        
        Args:
            limit: 样本数量
            
        Returns:
            性能数据列表
        """
        return await self._make_rpc_request(
            "getRecentPerformanceSamples",
            [limit]
        )
        
    def _validate_address(self, address: str) -> bool:
        """
        验证Solana地址格式
        
        Args:
            address: 地址字符串
            
        Returns:
            是否有效
            
        Raises:
            SolanaRPCError: 地址格式无效
        """
        try:
            # Solana地址是32字节的Base58编码
            decoded = base58.b58decode(address)
            if len(decoded) != 32:
                raise ValueError("地址长度不正确")
            return True
        except Exception:
            raise SolanaRPCError(f"无效的Solana地址格式: {address}")
            
    async def get_multiple_accounts_info(self, addresses: List[str]) -> List[Optional[SolanaAccountInfo]]:
        """
        批量获取多个账户信息
        
        Args:
            addresses: 地址列表
            
        Returns:
            账户信息列表
        """
        try:
            # 验证所有地址
            for addr in addresses:
                self._validate_address(addr)
                
            result = await self._make_rpc_request(
                "getMultipleAccounts",
                [
                    addresses,
                    {
                        "encoding": "jsonParsed",
                        "commitment": "confirmed"
                    }
                ]
            )
            
            accounts = []
            if result and result.get('value'):
                for i, account_data in enumerate(result['value']):
                    if account_data:
                        accounts.append(SolanaAccountInfo(
                            address=addresses[i],
                            lamports=account_data.get('lamports', 0),
                            owner=account_data.get('owner', ''),
                            executable=account_data.get('executable', False),
                            rent_epoch=account_data.get('rentEpoch', 0)
                        ))
                    else:
                        accounts.append(None)
            else:
                accounts = [None] * len(addresses)
                
            logger.info(f"批量获取 {len(addresses)} 个账户信息完成")
            return accounts
            
        except Exception as e:
            logger.error(f"批量获取账户信息失败: {str(e)}")
            raise SolanaRPCError(f"批量获取账户信息失败: {str(e)}")
            
    def get_connection_info(self) -> Dict[str, Any]:
        """
        获取连接信息
        
        Returns:
            连接配置信息
        """
        return {
            "network": self.network,
            "current_rpc_url": self.current_url,
            "all_rpc_urls": self.rpc_urls,
            "current_url_index": self.current_url_index,
            "failed_nodes": list(self.failed_nodes),
            "available_nodes": len(self.rpc_urls) - len(self.failed_nodes),
            "request_count": self._request_id,
            "session_active": self.session is not None,
            "last_health_check": self.last_health_check
        }
        
    async def get_node_status(self) -> Dict[str, Any]:
        """
        获取所有节点的状态信息
        
        Returns:
            节点状态字典
        """
        node_status = {}
        
        for url in self.rpc_urls:
            try:
                request_payload = {
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "getHealth"
                }
                
                async with self.session.post(url, json=request_payload) as response:
                    if response.status == 200:
                        result = await response.json()
                        node_status[url] = {
                            "status": "healthy" if result.get('result') == 'ok' else "unhealthy",
                            "response_time": response.headers.get('x-response-time', 'unknown'),
                            "is_current": url == self.current_url,
                            "is_failed": url in self.failed_nodes
                        }
                    else:
                        node_status[url] = {
                            "status": f"error_{response.status}",
                            "is_current": url == self.current_url,
                            "is_failed": url in self.failed_nodes
                        }
                        
            except Exception as e:
                node_status[url] = {
                    "status": f"unreachable: {str(e)}",
                    "is_current": url == self.current_url,
                    "is_failed": url in self.failed_nodes
                }
                
        return node_status