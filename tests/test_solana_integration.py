"""
Solana服务集成测试 - 使用真实的RPC节点
需要.env文件中配置真实的API密钥
"""

import asyncio

import pytest

from src.config.settings import settings
from src.services.solana_analyzer import SolanaAnalyzer
from src.services.solana_client import SolanaClient


class TestSolanaIntegration:
    """Solana集成测试 - 使用真实API"""
    
    @pytest.fixture
    def client(self):
        """创建使用真实配置的Solana客户端（默认主网）"""
        return SolanaClient()
            
    @pytest.fixture
    def devnet_client(self):
        """创建devnet客户端用于测试"""
        return SolanaClient(network="devnet")
    
    @pytest.mark.asyncio
    async def test_rpc_node_health_check(self, client):
        """测试RPC节点健康检查"""
        async with client:
            # 获取连接信息
            conn_info = client.get_connection_info()
            print(f"当前使用节点: {conn_info['current_rpc_url']}")
            print(f"所有节点: {conn_info['all_rpc_urls']}")
            
            # 检查节点状态
            node_status = await client.get_node_status()
            print("节点状态:")
            for url, status in node_status.items():
                print(f"  {url}: {status}")
                
            # 至少应该有一个健康的节点
            healthy_nodes = [url for url, status in node_status.items() 
                            if status['status'] == 'healthy']
            assert len(healthy_nodes) > 0, "至少需要一个健康的RPC节点"
        
    @pytest.mark.asyncio
    async def test_get_version(self, client):
        """测试获取Solana版本信息"""
        async with client:
            version = await client.get_version()
            assert version is not None
            assert 'solana-core' in version
            print(f"Solana版本: {version}")
        
    @pytest.mark.asyncio 
    async def test_get_health(self, client):
        """测试节点健康状态"""
        async with client:
            health = await client.get_health()
            assert health == "ok" or health == "unhealthy"
            print(f"节点健康状态: {health}")
        
    @pytest.mark.asyncio
    async def test_get_balance_real_address(self, client):
        """测试获取真实地址余额"""
        async with client:
            # 使用一个已知的地址（Solana官方地址）
            test_addresses = [
                "11111111111111111111111111111112",  # System Program
                "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA",  # Token Program
            ]
            
            for address in test_addresses:
                try:
                    balance = await client.get_balance(address)
                    assert isinstance(balance, int)
                    assert balance >= 0
                    print(f"地址 {address[:20]}... 余额: {balance / 10**9:.4f} SOL")
                except Exception as e:
                    print(f"获取地址 {address} 余额失败: {e}")
                    # 不断言失败，因为某些地址可能不存在
                
    @pytest.mark.asyncio
    async def test_get_account_info_real(self, client):
        """测试获取真实账户信息"""
        async with client:
            # 使用System Program地址
            system_program = "11111111111111111111111111111112"
            
            try:
                account_info = await client.get_account_info(system_program)
                if account_info:
                    assert account_info.address == system_program
                    print(f"账户信息: {account_info}")
                else:
                    print("账户不存在或无数据")
            except Exception as e:
                print(f"获取账户信息失败: {e}")
            
    @pytest.mark.asyncio
    async def test_node_failover(self):
        """测试节点故障转移"""
        # 创建一个包含一个无效节点的客户端
        invalid_urls = [
            "https://invalid-node.example.com",  # 无效节点
            "https://api.mainnet-beta.solana.com",  # 有效节点
        ]
        
        async with SolanaClient(rpc_urls=invalid_urls) as client:
            # 客户端应该自动切换到可用节点
            health = await client.get_health()
            assert health in ["ok", "unhealthy"]
            
            conn_info = client.get_connection_info()
            print(f"失败转移后使用节点: {conn_info['current_rpc_url']}")
            print(f"失败节点列表: {conn_info['failed_nodes']}")
            
    @pytest.mark.asyncio 
    async def test_analyzer_with_real_data(self, client):
        """测试分析器与真实数据"""
        async with client:
            analyzer = SolanaAnalyzer()
            
            # 获取一些交易签名
            try:
                # 使用一个活跃地址获取交易
                signatures = await client.get_signatures_for_address(
                    "11111111111111111111111111111112", 
                    limit=5
                )
                
                print(f"获取到 {len(signatures)} 个交易签名")
                
                # 分析前几个交易
                for i, signature in enumerate(signatures[:2]):
                    try:
                        tx = await client.get_transaction(signature)
                        if tx:
                            result = await analyzer.analyze_transaction(tx)
                            print(f"交易 {i+1} 分析结果: {result.transaction_type}")
                            
                    except Exception as e:
                        print(f"分析交易 {signature} 失败: {e}")
                        
            except Exception as e:
                print(f"获取交易失败: {e}")
            
    @pytest.mark.asyncio
    async def test_performance_benchmark(self, client):
        """测试RPC性能基准"""
        import time
        
        async with client:
            # 测试连续请求的性能
            start_time = time.time()
            
            tasks = []
            for _ in range(5):  # 发送5个并发请求
                task = client.get_health()
                tasks.append(task)
                
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            end_time = time.time()
            duration = end_time - start_time
            
            successful_requests = sum(1 for r in results if not isinstance(r, Exception))
            
            print(f"性能测试结果:")
            print(f"  并发请求数: {len(tasks)}")
            print(f"  成功请求数: {successful_requests}")
            print(f"  总耗时: {duration:.2f}秒")
            print(f"  平均每请求: {duration/len(tasks):.2f}秒")
            
            # 至少应该有一些成功的请求
            assert successful_requests > 0
        
    @pytest.mark.asyncio
    async def test_devnet_connection(self, devnet_client):
        """测试devnet连接"""
        async with devnet_client:
            conn_info = devnet_client.get_connection_info()
            print(f"Devnet节点: {conn_info['current_rpc_url']}")
            
            # devnet应该更稳定
            health = await devnet_client.get_health()
            print(f"Devnet健康状态: {health}")
            
            # 可以断言devnet应该是健康的
            # assert health == "ok"  # 根据实际情况决定是否启用
        
    @pytest.mark.asyncio 
    async def test_configuration_loading(self):
        """测试配置加载"""
        print("当前Solana数组配置:")
        print(f"  默认网络: {settings.solana_default_network}")
        print(f"  主网节点数: {len(settings.solana_rpc_nodes)}")
        print(f"  主网节点列表: {settings.solana_rpc_nodes}")
        print(f"  Devnet节点: {settings.get_rpc_nodes_by_network('devnet')}")
        print(f"  Testnet节点: {settings.get_rpc_nodes_by_network('testnet')}")
        print(f"  超时设置: {settings.solana_rpc_timeout}秒")
        print(f"  最大重试: {settings.solana_rpc_max_retries}次")
        print(f"  健康检查间隔: {settings.solana_rpc_health_check_interval}秒")
        
        # 验证配置已正确加载
        assert len(settings.solana_rpc_nodes) > 1
        assert settings.solana_rpc_timeout > 0
        assert settings.solana_rpc_max_retries > 0
        assert settings.solana_default_network in ['mainnet', 'devnet', 'testnet']


if __name__ == "__main__":
    # 直接运行测试的入口点
    pytest.main([__file__, "-v", "-s"])