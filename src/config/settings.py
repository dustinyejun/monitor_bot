from typing import List

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """应用程序配置"""
    
    # 数据库配置
    database_url: str = "postgresql://postgres:password@localhost:5432/monitor_bot"
    
    # API配置
    twitter_bearer_token: str = ""
    
    # Solana RPC配置 - 数组格式
    solana_rpc_mainnet_urls: str = "https://api.mainnet-beta.solana.com,https://solana-api.projectserum.com,https://api.metaplex.solana.com,https://solana.public-rpc.com,https://rpc.ankr.com/solana"
    solana_rpc_devnet_urls: str = "https://api.devnet.solana.com"
    solana_rpc_testnet_urls: str = "https://api.testnet.solana.com"
    
    # 默认网络
    solana_default_network: str = "mainnet"
    
    # RPC参数配置
    solana_rpc_timeout: int = 30
    solana_rpc_max_retries: int = 3
    solana_rpc_health_check_interval: int = 300


    
    wechat_webhook_url: str = ""
    
    # 插件化监控配置
    enabled_monitors: str = "twitter,solana"
    
    # Twitter监控插件
    twitter_monitor_enabled: bool = True
    twitter_check_interval: int = 60  # 秒
    
    # Solana监控插件
    solana_monitor_enabled: bool = True
    solana_check_interval: int = 30   # 秒
    
    # Solana DEX 监控配置 - 不同交易类型的监控金额阈值(USD)
    sol_transfer_amount: float = 0.01         # 原生SOL代币转账监控金额
    token_transfer_amount: float = 0.01       # 代币转账监控金额
    dex_swap_amount: float = 0.01             # DEX交易监控金额
    dex_add_liquidity_amount: float = 0.01    # DEX添加流动性监控金额
    dex_remove_liquidity_amount: float = 0.01 # DEX移除流动性监控金额
    
    # 通用监控配置
    monitor_startup_delay: int = 10
    monitor_graceful_shutdown_timeout: int = 30
    
    # 应用配置
    debug: bool = False
    log_level: str = "INFO"
    
    # 服务配置
    host: str = "0.0.0.0"
    port: int = 8000
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        
    def _parse_rpc_urls(self, urls_string: str) -> List[str]:
        """解析逗号分隔的RPC URL字符串"""
        if not urls_string:
            return []
        return [url.strip() for url in urls_string.split(',') if url.strip()]
    
    @property
    def solana_rpc_nodes(self) -> List[str]:
        """获取主网RPC节点列表（向后兼容）"""
        return self._parse_rpc_urls(self.solana_rpc_mainnet_urls)
        
    def get_rpc_nodes_by_network(self, network: str = None) -> List[str]:
        """根据网络类型获取RPC节点列表"""
        if network is None:
            network = self.solana_default_network
            
        network = network.lower()
        if network == "devnet":
            return self._parse_rpc_urls(self.solana_rpc_devnet_urls)
        elif network == "testnet":
            return self._parse_rpc_urls(self.solana_rpc_testnet_urls)
        else:  # mainnet
            return self._parse_rpc_urls(self.solana_rpc_mainnet_urls)
    
    def get_enabled_monitors(self) -> List[str]:
        """获取启用的监控插件列表"""
        if not self.enabled_monitors:
            return []
        return [monitor.strip().lower() for monitor in self.enabled_monitors.split(',') 
                if monitor.strip()]
    
    def is_monitor_enabled(self, monitor_name: str) -> bool:
        """检查指定监控插件是否启用"""
        monitor_name = monitor_name.lower()
        enabled_monitors = self.get_enabled_monitors()
        
        # 检查是否在启用列表中
        if monitor_name not in enabled_monitors:
            return False
            
        # 检查对应的enabled配置
        if monitor_name == "twitter":
            return self.twitter_monitor_enabled
        elif monitor_name == "solana":
            return self.solana_monitor_enabled
        
        return True  # 默认启用


# 创建全局配置实例
settings = Settings()