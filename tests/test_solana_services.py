"""
Solana服务相关的单元测试
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timezone
from decimal import Decimal

from src.services.solana_client import (
    SolanaClient, SolanaAccountInfo, SolanaTransaction, 
    SolanaTokenInfo, SolanaRPCError
)
from src.services.solana_analyzer import (
    SolanaAnalyzer, TransactionType, DEXPlatform, 
    AnalysisResult, SwapInfo, TransferInfo, TokenInfo
)
from src.services.solana_monitor import SolanaMonitorService

# 配置pytest-asyncio
pytest_plugins = ('pytest_asyncio',)


class TestSolanaClient:
    """Solana客户端测试"""
    
    @pytest.fixture
    def client(self):
        """创建测试客户端"""
        return SolanaClient(network="testnet")
        
    @pytest.mark.asyncio
    async def test_health_check_success(self, client):
        """测试RPC健康检查成功"""
        with patch.object(client, '_make_rpc_request', new_callable=AsyncMock) as mock_request:
            mock_request.return_value = "ok"
            
            async with client:
                result = await client.get_health()
                
            assert result == "ok"
            mock_request.assert_called_with("getHealth")
            
    @pytest.mark.asyncio
    async def test_health_check_failure(self, client):
        """测试RPC健康检查失败"""
        with patch.object(client, '_make_rpc_request', new_callable=AsyncMock) as mock_request:
            mock_request.side_effect = SolanaRPCError("RPC节点不可用")
            
            async with client:
                result = await client.get_health()
                
            assert result == "unhealthy"
            
    @pytest.mark.asyncio
    async def test_get_version(self, client):
        """测试获取节点版本"""
        mock_version = {
            "solana-core": "1.16.0",
            "feature-set": 2345
        }
        
        with patch.object(client, '_make_rpc_request', new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_version
            
            async with client:
                result = await client.get_version()
                
            assert result == mock_version
            
    @pytest.mark.asyncio
    async def test_get_balance_success(self, client):
        """测试成功获取余额"""
        test_address = "9WzDXwBbmkg8ZTbNMqUxvQRAyrZzDsGYdLVL9zYtAWWM"
        mock_response = {"value": 1000000000}  # 1 SOL in lamports
        
        with patch.object(client, '_make_rpc_request', new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response
            
            async with client:
                balance = await client.get_balance(test_address)
                
            assert balance == 1000000000
            mock_request.assert_called_with("getBalance", [test_address])
            
    @pytest.mark.asyncio
    async def test_get_balance_invalid_address(self, client):
        """测试无效地址余额查询"""
        invalid_address = "invalid_address"
        
        async with client:
            with pytest.raises(SolanaRPCError) as exc_info:
                await client.get_balance(invalid_address)
                
            assert "无效的Solana地址格式" in str(exc_info.value)
            
    @pytest.mark.asyncio
    async def test_get_account_info_success(self, client):
        """测试成功获取账户信息"""
        test_address = "9WzDXwBbmkg8ZTbNMqUxvQRAyrZzDsGYdLVL9zYtAWWM"
        mock_response = {
            "value": {
                "lamports": 1000000000,
                "owner": "11111111111111111111111111111111",
                "executable": False,
                "rentEpoch": 200
            }
        }
        
        with patch.object(client, '_make_rpc_request', new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response
            
            async with client:
                account_info = await client.get_account_info(test_address)
                
            assert account_info is not None
            assert account_info.address == test_address
            assert account_info.lamports == 1000000000
            assert account_info.sol_balance == Decimal('1')
            
    @pytest.mark.asyncio
    async def test_get_account_info_not_exists(self, client):
        """测试获取不存在的账户信息"""
        test_address = "9WzDXwBbmkg8ZTbNMqUxvQRAyrZzDsGYdLVL9zYtAWWM"
        mock_response = {"value": None}
        
        with patch.object(client, '_make_rpc_request', new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response
            
            async with client:
                account_info = await client.get_account_info(test_address)
                
            assert account_info is None
            
    @pytest.mark.asyncio
    async def test_get_token_accounts(self, client):
        """测试获取代币账户"""
        test_address = "9WzDXwBbmkg8ZTbNMqUxvQRAyrZzDsGYdLVL9zYtAWWM"
        mock_response = {
            "value": [
                {
                    "account": {
                        "data": {
                            "parsed": {
                                "info": {
                                    "mint": "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
                                    "tokenAmount": {
                                        "amount": "1000000",
                                        "decimals": 6,
                                        "uiAmount": 1.0,
                                        "uiAmountString": "1.0"
                                    }
                                }
                            }
                        }
                    }
                }
            ]
        }
        
        with patch.object(client, '_make_rpc_request', new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response
            
            async with client:
                tokens = await client.get_token_accounts(test_address)
                
            assert len(tokens) == 1
            assert tokens[0].mint == "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"
            assert tokens[0].amount == 1000000
            assert tokens[0].decimals == 6
            assert tokens[0].balance == Decimal('1')
            
    @pytest.mark.asyncio
    async def test_get_signatures_for_address(self, client):
        """测试获取地址交易签名"""
        test_address = "9WzDXwBbmkg8ZTbNMqUxvQRAyrZzDsGYdLVL9zYtAWWM"
        mock_signatures = [
            {"signature": "sig1"},
            {"signature": "sig2"},
            {"signature": "sig3"}
        ]
        
        with patch.object(client, '_make_rpc_request', new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_signatures
            
            async with client:
                signatures = await client.get_signatures_for_address(test_address, limit=3)
                
            assert signatures == ["sig1", "sig2", "sig3"]
            
    @pytest.mark.asyncio
    async def test_rpc_error_handling(self, client):
        """测试RPC错误处理"""
        test_address = "9WzDXwBbmkg8ZTbNMqUxvQRAyrZzDsGYdLVL9zYtAWWM"
        
        with patch.object(client, '_make_rpc_request', new_callable=AsyncMock) as mock_request:
            mock_request.side_effect = SolanaRPCError("网络连接失败", code=500)
            
            async with client:
                with pytest.raises(SolanaRPCError) as exc_info:
                    await client.get_balance(test_address)
                    
                # 由于异常被重新包装，检查消息内容而不是code
                assert "获取余额失败" in str(exc_info.value)


class TestSolanaAnalyzer:
    """Solana分析器测试"""
    
    @pytest.fixture
    def analyzer(self):
        """创建测试分析器"""
        return SolanaAnalyzer()
        
    @pytest.fixture
    def sample_transaction(self):
        """创建样本交易"""
        return SolanaTransaction(
            signature="test_signature_123",
            slot=12345,
            block_time=int(datetime.now(timezone.utc).timestamp()),
            fee=5000,
            accounts=["account1", "account2"],
            instructions=[],
            pre_balances=[1000000000, 0],
            post_balances=[995000000, 5000000],  # 转账示例
            err=None
        )
        
    @pytest.mark.asyncio
    async def test_analyze_sol_transfer(self, analyzer, sample_transaction):
        """测试SOL转账分析"""
        result = await analyzer.analyze_transaction(sample_transaction)
        
        assert result.transaction_type == TransactionType.SOL_TRANSFER
        assert result.gas_fee_sol == Decimal('0.000005')
        assert result.risk_level in ["low", "medium", "high"]
        
    @pytest.mark.asyncio
    async def test_analyze_dex_swap(self, analyzer):
        """测试DEX交换分析"""
        # 创建包含Raydium程序交互的交易
        swap_transaction = SolanaTransaction(
            signature="swap_signature_123",
            slot=12345,
            block_time=int(datetime.now(timezone.utc).timestamp()),
            fee=5000,
            accounts=["account1", "account2"],
            instructions=[
                {"programId": "9WzDXwBbmkg8ZTbNMqUxvQRAyrZzDsGYdLVL9zYtAWWM"}  # Raydium
            ],
            pre_balances=[1000000000, 0],
            post_balances=[900000000, 100000000],
            err=None
        )
        
        result = await analyzer.analyze_transaction(swap_transaction)
        
        assert result.transaction_type == TransactionType.DEX_SWAP
        assert result.dex_platform == DEXPlatform.RAYDIUM
        
    @pytest.mark.asyncio
    async def test_analyze_failed_transaction(self, analyzer):
        """测试失败交易分析"""
        failed_transaction = SolanaTransaction(
            signature="failed_signature_123",
            slot=12345,
            block_time=int(datetime.now(timezone.utc).timestamp()),
            fee=5000,
            accounts=["account1", "account2"],
            instructions=[],
            pre_balances=[1000000000, 0],
            post_balances=[995000000, 0],  # 只扣除了手续费
            err={"InstructionError": [0, "Custom"]}
        )
        
        result = await analyzer.analyze_transaction(failed_transaction)
        
        assert not result.transaction.is_success
        assert "transaction_failed" in result.risk_factors
        assert result.risk_level in ["medium", "high"]
        
    def test_get_token_info_known_tokens(self, analyzer):
        """测试已知代币信息获取"""
        # 测试SOL
        sol_info = asyncio.run(analyzer.get_token_info("11111111111111111111111111111111"))
        assert sol_info is not None
        assert sol_info.symbol == "SOL"
        
        # 测试USDC
        usdc_info = asyncio.run(analyzer.get_token_info("EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"))
        assert usdc_info is not None
        assert usdc_info.symbol == "USDC"
        
    def test_get_token_info_unknown_token(self, analyzer):
        """测试未知代币信息"""
        unknown_info = asyncio.run(analyzer.get_token_info("UnknownMintAddress123456789"))
        assert unknown_info is None
        
    @pytest.mark.asyncio
    async def test_price_fetching(self, analyzer):
        """测试价格获取"""
        # 测试获取SOL价格（使用模拟价格）
        sol_price = await analyzer._get_token_price("SOL")
        assert sol_price is not None
        assert sol_price > 0
        
        # 测试价格缓存
        cached_price = await analyzer._get_token_price("SOL")
        assert cached_price == sol_price
        
    def test_batch_analysis(self, analyzer):
        """测试批量交易分析"""
        transactions = [
            SolanaTransaction(
                signature=f"batch_sig_{i}",
                slot=12345 + i,
                block_time=int(datetime.now(timezone.utc).timestamp()),
                fee=5000,
                accounts=["account1", "account2"],
                instructions=[],
                pre_balances=[1000000000, 0],
                post_balances=[995000000, 5000000],
                err=None
            )
            for i in range(3)
        ]
        
        results = analyzer.analyze_batch_transactions(transactions)
        
        assert len(results) == 3
        assert all(isinstance(result, AnalysisResult) for result in results)
        
    def test_summary_stats(self, analyzer):
        """测试统计摘要"""
        # 创建测试结果
        results = []
        for i in range(5):
            tx = SolanaTransaction(
                signature=f"stats_sig_{i}",
                slot=12345 + i,
                err=None if i < 4 else {"error": "failed"}
            )
            result = AnalysisResult(
                transaction=tx,
                transaction_type=TransactionType.SOL_TRANSFER if i < 3 else TransactionType.DEX_SWAP,
                dex_platform=DEXPlatform.RAYDIUM if i >= 3 else DEXPlatform.UNKNOWN,
                total_value_usd=Decimal('100') * (i + 1),
                risk_level="low" if i < 2 else "medium"
            )
            results.append(result)
            
        stats = analyzer.get_summary_stats(results)
        
        assert stats['total_transactions'] == 5
        assert stats['successful_transactions'] == 4
        assert stats['success_rate'] == 0.8
        assert stats['transaction_types']['sol_transfer'] == 3
        assert stats['transaction_types']['dex_swap'] == 2
        assert stats['total_value_usd'] == 1500.0  # 100+200+300+400+500


class TestSolanaMonitorService:
    """Solana监控服务测试"""
    
    @pytest.fixture
    def monitor_service(self):
        """创建测试监控服务"""
        return SolanaMonitorService()
        
    def test_add_wallet(self, monitor_service):
        """测试添加钱包"""
        test_address = "9WzDXwBbmkg8ZTbNMqUxvQRAyrZzDsGYdLVL9zYtAWWM"
        
        with patch('src.services.solana_monitor.get_db') as mock_get_db:
            mock_db = Mock()
            mock_get_db.return_value.__enter__.return_value = mock_db
            mock_db.execute.return_value.scalar_one_or_none.return_value = None
            
            # 模拟创建的钱包对象
            mock_wallet = Mock()
            mock_wallet.id = 1
            mock_wallet.address = test_address
            mock_wallet.label = "Test Wallet"
            mock_wallet.created_at = datetime.now()
            mock_wallet.updated_at = datetime.now()
            
            mock_db.refresh.return_value = None
            
            with patch('src.services.solana_monitor.SolanaWalletResponse.model_validate') as mock_validate:
                mock_response = Mock()
                mock_validate.return_value = mock_response
                
                result = monitor_service.add_wallet(test_address, "Test Wallet")
                
                assert mock_db.add.called
                assert mock_db.commit.called
                assert mock_validate.called
                
    def test_add_existing_wallet(self, monitor_service):
        """测试添加已存在的钱包"""
        test_address = "9WzDXwBbmkg8ZTbNMqUxvQRAyrZzDsGYdLVL9zYtAWWM"
        
        with patch('src.services.solana_monitor.get_db') as mock_get_db:
            mock_db = Mock()
            mock_get_db.return_value.__enter__.return_value = mock_db
            
            existing_wallet = Mock()
            existing_wallet.address = test_address
            mock_db.execute.return_value.scalar_one_or_none.return_value = existing_wallet
            
            with patch('src.services.solana_monitor.SolanaWalletResponse.model_validate') as mock_validate:
                mock_validate.return_value = Mock()
                result = monitor_service.add_wallet(test_address)
                
                assert not mock_db.add.called
                assert mock_validate.called
                
    def test_remove_wallet(self, monitor_service):
        """测试移除钱包"""
        test_address = "9WzDXwBbmkg8ZTbNMqUxvQRAyrZzDsGYdLVL9zYtAWWM"
        
        with patch('src.services.solana_monitor.get_db') as mock_get_db:
            mock_db = Mock()
            mock_get_db.return_value.__enter__.return_value = mock_db
            
            existing_wallet = Mock()
            mock_db.execute.return_value.scalar_one_or_none.return_value = existing_wallet
            
            result = monitor_service.remove_wallet(test_address)
            
            assert result is True
            mock_db.delete.assert_called_with(existing_wallet)
            assert mock_db.commit.called
            
    def test_update_wallet_status(self, monitor_service):
        """测试更新钱包状态"""
        test_address = "9WzDXwBbmkg8ZTbNMqUxvQRAyrZzDsGYdLVL9zYtAWWM"
        
        with patch('src.services.solana_monitor.get_db') as mock_get_db:
            mock_db = Mock()
            mock_get_db.return_value.__enter__.return_value = mock_db
            
            existing_wallet = Mock()
            existing_wallet.is_active = True
            mock_db.execute.return_value.scalar_one_or_none.return_value = existing_wallet
            
            result = monitor_service.update_wallet_status(test_address, False)
            
            assert result is True
            assert existing_wallet.is_active is False
            assert mock_db.commit.called
            
    def test_filter_transaction_by_excluded_tokens(self, monitor_service):
        """测试按排除代币过滤交易"""
        # 创建分析结果
        excluded_token = TokenInfo(mint="excluded_token_mint")
        transfer_info = TransferInfo(
            from_address="from_addr",
            to_address="to_addr",
            token=excluded_token,
            amount=Decimal('100')
        )
        
        analysis_result = AnalysisResult(
            transaction=Mock(),
            transaction_type=TransactionType.TOKEN_TRANSFER,
            transfer_info=transfer_info
        )
        
        # 创建钱包对象（排除指定代币）
        wallet = Mock()
        wallet.exclude_tokens = ["excluded_token_mint"]
        
        # 测试过滤
        should_filter = monitor_service._should_filter_transaction(analysis_result, wallet)
        assert should_filter is True
        
    def test_filter_small_amount_transaction(self, monitor_service):
        """测试过滤小额交易"""
        analysis_result = AnalysisResult(
            transaction=Mock(),
            transaction_type=TransactionType.SOL_TRANSFER,
            total_value_usd=Decimal('0.5')  # 小于1美元
        )
        
        wallet = Mock()
        wallet.exclude_tokens = []
        
        should_filter = monitor_service._should_filter_transaction(analysis_result, wallet)
        assert should_filter is True
        
    @pytest.mark.asyncio
    async def test_get_wallet_balance(self, monitor_service):
        """测试获取钱包余额"""
        test_address = "9WzDXwBbmkg8ZTbNMqUxvQRAyrZzDsGYdLVL9zYtAWWM"
        
        with patch('src.services.solana_monitor.SolanaClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            
            # 模拟余额和代币账户
            mock_client.get_balance = AsyncMock(return_value=1000000000)  # 1 SOL
            mock_client.get_token_accounts = AsyncMock(return_value=[
                SolanaTokenInfo(
                    mint="EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
                    amount=1000000,
                    decimals=6,
                    ui_amount=1.0
                )
            ])
            
            result = await monitor_service.get_wallet_balance(test_address)
            
            assert result['address'] == test_address
            assert result['sol_balance'] == 1.0
            assert len(result['tokens']) == 1
            assert result['tokens'][0]['mint'] == "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"
            
    def test_get_statistics(self, monitor_service):
        """测试获取统计信息"""
        with patch('src.services.solana_monitor.get_db') as mock_get_db:
            mock_db = Mock()
            mock_get_db.return_value.__enter__.return_value = mock_db
            
            # 模拟钱包和交易数据
            mock_wallets = [Mock(is_active=True), Mock(is_active=False)]
            mock_transactions = [
                Mock(
                    is_success=True,
                    created_at=datetime.now(timezone.utc),
                    transaction_type='sol_transfer',
                    dex_platform='unknown',
                    amount_usd=100.0,
                    is_processed=False,
                    is_notified=False
                )
            ]
            
            mock_db.execute.return_value.scalars.return_value.all.side_effect = [
                mock_wallets,  # 钱包查询
                mock_transactions  # 交易查询
            ]
            
            result = monitor_service.get_statistics()
            
            assert result['total_wallets'] == 2
            assert result['active_wallets'] == 1
            assert result['total_transactions'] == 1
            assert result['successful_transactions'] == 1
            assert result['success_rate'] == 1.0


if __name__ == "__main__":
    pytest.main([__file__])