"""
监控插件系统测试
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime

from src.core.monitor_plugin import MonitorPlugin, MonitorStatus, plugin_registry
from src.core.monitor_manager import MonitorManager
from src.config.settings import settings
from src.plugins.twitter_monitor_plugin import TwitterMonitorPlugin
from src.plugins.solana_monitor_plugin import SolanaMonitorPlugin


class TestMonitorPlugin:
    """监控插件基类测试"""
    
    class DummyPlugin(MonitorPlugin):
        """测试用的虚拟插件"""
        
        def __init__(self, name: str, config: dict = None):
            super().__init__(name, config)
            self.initialized = False
            self.check_called = False
            self.cleanup_called = False
        
        @property
        def check_interval(self) -> int:
            return self.get_config("interval", 5)
        
        async def initialize(self) -> bool:
            await asyncio.sleep(0.1)  # 模拟初始化时间
            self.initialized = True
            return True
        
        async def check(self) -> bool:
            await asyncio.sleep(0.1)  # 模拟检查时间
            self.check_called = True
            return True
        
        async def cleanup(self):
            await asyncio.sleep(0.1)  # 模拟清理时间
            self.cleanup_called = True
    
    def test_plugin_creation(self):
        """测试插件创建"""
        plugin = self.DummyPlugin("test", {"interval": 10})
        
        assert plugin.name == "test"
        assert plugin.check_interval == 10
        assert plugin.stats.status == MonitorStatus.STOPPED
        assert not plugin.is_running()
    
    @pytest.mark.asyncio
    async def test_plugin_lifecycle(self):
        """测试插件生命周期"""
        plugin = self.DummyPlugin("test")
        
        # 启动插件
        assert await plugin.start()
        assert plugin.initialized
        assert plugin.is_running()
        assert plugin.stats.status == MonitorStatus.RUNNING
        
        # 等待一下检查被调用
        await asyncio.sleep(0.2)
        
        # 停止插件
        assert await plugin.stop()
        assert plugin.cleanup_called
        assert plugin.stats.status == MonitorStatus.STOPPED
        assert not plugin.is_running()


class TestPluginRegistry:
    """插件注册表测试"""
    
    def test_plugin_registration(self):
        """测试插件注册"""
        # 检查预注册的插件
        assert "twitter" in plugin_registry.get_available_plugins()
        assert "solana" in plugin_registry.get_available_plugins()
        
        # 获取插件类
        twitter_class = plugin_registry.get_plugin_class("twitter")
        assert twitter_class == TwitterMonitorPlugin
        
        solana_class = plugin_registry.get_plugin_class("solana")
        assert solana_class == SolanaMonitorPlugin
    
    def test_plugin_creation_via_registry(self):
        """测试通过注册表创建插件"""
        config = {"check_interval": 30, "test_param": "test_value"}
        
        # 创建Twitter插件
        twitter_plugin = plugin_registry.create_plugin("twitter", config)
        assert isinstance(twitter_plugin, TwitterMonitorPlugin)
        assert twitter_plugin.name == "twitter"
        assert twitter_plugin.get_config("test_param") == "test_value"
        
        # 创建不存在的插件
        invalid_plugin = plugin_registry.create_plugin("invalid", config)
        assert invalid_plugin is None


class TestMonitorManager:
    """监控管理器测试"""
    
    @pytest.fixture
    def manager(self):
        """创建监控管理器实例"""
        return MonitorManager()
    
    @pytest.mark.asyncio
    async def test_load_plugins(self, manager):
        """测试加载插件"""
        with patch.object(settings, 'get_enabled_monitors', return_value=['twitter', 'solana']):
            with patch.object(settings, 'is_monitor_enabled', return_value=True):
                success = await manager.load_plugins()
                assert success
                assert len(manager.get_plugin_names()) == 2
                assert "twitter" in manager.get_plugin_names()
                assert "solana" in manager.get_plugin_names()
    
    @pytest.mark.asyncio 
    async def test_plugin_config_generation(self, manager):
        """测试插件配置生成"""
        # 测试Twitter插件配置
        twitter_config = manager._get_plugin_config("twitter")
        assert "check_interval" in twitter_config
        assert "bearer_token" in twitter_config
        
        # 测试Solana插件配置
        solana_config = manager._get_plugin_config("solana")
        assert "check_interval" in solana_config
        assert "rpc_nodes" in solana_config
        assert "default_network" in solana_config
    
    @pytest.mark.asyncio
    async def test_health_check(self, manager):
        """测试健康检查"""
        # 空管理器的健康检查
        health = await manager.health_check()
        assert health["total_plugins"] == 0
        assert health["running_plugins"] == 0
        assert health["health_score"] == 0
        assert not health["manager_running"]


class TestTwitterMonitorPlugin:
    """Twitter监控插件测试"""
    
    @pytest.fixture
    def plugin(self):
        """创建Twitter插件实例"""
        config = {
            "check_interval": 30,
            "bearer_token": "test_token"
        }
        return TwitterMonitorPlugin("twitter", config)
    
    def test_plugin_info(self, plugin):
        """测试插件信息"""
        info = plugin.get_plugin_info()
        assert info["name"] == "twitter"
        assert info["type"] == "twitter_monitor"
        assert info["version"] == "1.0.0"
        assert "description" in info
        assert info["config"]["check_interval"] == 30
        assert info["config"]["bearer_token_configured"] is True
    
    @pytest.mark.asyncio
    async def test_initialize_without_token(self):
        """测试无Token初始化"""
        plugin = TwitterMonitorPlugin("twitter", {})
        success = await plugin.initialize()
        assert not success  # 应该失败，因为没有token
    
    @pytest.mark.asyncio
    async def test_initialize_with_mock_client(self, plugin):
        """测试使用Mock客户端初始化"""
        with patch('src.plugins.twitter_monitor_plugin.TwitterClient'):
            with patch.object(plugin, '_test_api_connection', return_value=True):
                with patch('src.plugins.twitter_monitor_plugin.TwitterAnalyzer'):
                    with patch('src.plugins.twitter_monitor_plugin.TwitterMonitorService'):
                        success = await plugin.initialize()
                        assert success


class TestSolanaMonitorPlugin:
    """Solana监控插件测试"""
    
    @pytest.fixture
    def plugin(self):
        """创建Solana插件实例"""
        config = {
            "check_interval": 30,
            "rpc_nodes": ["https://api.mainnet-beta.solana.com"],
            "default_network": "mainnet"
        }
        return SolanaMonitorPlugin("solana", config)
    
    def test_plugin_info(self, plugin):
        """测试插件信息"""
        info = plugin.get_plugin_info()
        assert info["name"] == "solana"
        assert info["type"] == "solana_monitor"
        assert info["version"] == "1.0.0"
        assert "description" in info
        assert info["config"]["check_interval"] == 30
        assert info["config"]["network"] == "mainnet"
        assert info["config"]["rpc_nodes_count"] == 1
    
    @pytest.mark.asyncio
    async def test_initialize_without_rpc(self):
        """测试无RPC节点初始化"""
        plugin = SolanaMonitorPlugin("solana", {})
        success = await plugin.initialize()
        assert not success  # 应该失败，因为没有RPC节点
    
    @pytest.mark.asyncio
    async def test_initialize_with_mock_client(self, plugin):
        """测试使用Mock客户端初始化"""
        with patch('src.plugins.solana_monitor_plugin.SolanaClient'):
            with patch.object(plugin, '_test_rpc_connection', return_value=True):
                with patch('src.plugins.solana_monitor_plugin.SolanaAnalyzer'):
                    with patch('src.plugins.solana_monitor_plugin.SolanaMonitorService'):
                        success = await plugin.initialize()
                        assert success
    
    @pytest.mark.asyncio
    async def test_get_wallet_balance_mock(self, plugin):
        """测试获取钱包余额（Mock）"""
        mock_client = AsyncMock()
        mock_client.get_balance = AsyncMock(return_value=1000000000)  # 1 SOL
        mock_client.get_token_accounts = AsyncMock(return_value=[])
        
        with patch('src.plugins.solana_monitor_plugin.SolanaClient') as mock_client_class:
            mock_client_class.return_value.__aenter__.return_value = mock_client
            
            balance_info = await plugin.get_wallet_balance("test_address")
            
            assert balance_info["address"] == "test_address"
            assert balance_info["sol_balance"] == 1.0
            assert balance_info["token_count"] == 0


class TestPluginConfiguration:
    """插件配置测试"""
    
    def test_enabled_monitors_parsing(self):
        """测试启用监控列表解析"""
        monitors = settings.get_enabled_monitors()
        assert isinstance(monitors, list)
        assert len(monitors) > 0
        
        # 测试单独检查
        assert settings.is_monitor_enabled("twitter") == settings.twitter_monitor_enabled
        assert settings.is_monitor_enabled("solana") == settings.solana_monitor_enabled
    
    def test_plugin_specific_config(self):
        """测试插件特定配置"""
        # Twitter配置
        assert hasattr(settings, 'twitter_monitor_enabled')
        assert hasattr(settings, 'twitter_check_interval')
        
        # Solana配置
        assert hasattr(settings, 'solana_monitor_enabled')
        assert hasattr(settings, 'solana_check_interval')
        
        # 通用配置
        assert hasattr(settings, 'monitor_startup_delay')
        assert hasattr(settings, 'monitor_graceful_shutdown_timeout')


if __name__ == "__main__":
    pytest.main([__file__, "-v"])