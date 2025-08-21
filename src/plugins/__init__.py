"""
监控插件模块
包含所有可用的监控插件
"""

# 导入插件以触发注册
from .twitter_monitor_plugin import TwitterMonitorPlugin
from .solana_monitor_plugin import SolanaMonitorPlugin

__all__ = [
    "TwitterMonitorPlugin",
    "SolanaMonitorPlugin"
]