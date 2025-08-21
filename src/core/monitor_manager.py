"""
监控管理器
负责管理所有监控插件的生命周期
"""

import asyncio
from typing import Dict, List, Optional, Any
from contextlib import asynccontextmanager

from .monitor_plugin import MonitorPlugin, MonitorStats, plugin_registry
from ..config.settings import settings
from ..utils.logger import logger


class MonitorManager:
    """监控管理器"""
    
    def __init__(self):
        self._plugins: Dict[str, MonitorPlugin] = {}
        self._running = False
    
    async def load_plugins(self) -> bool:
        """
        根据配置加载插件
        
        Returns:
            是否加载成功
        """
        enabled_monitors = settings.get_enabled_monitors()
        logger.info(f"准备加载监控插件: {enabled_monitors}")
        
        success_count = 0
        
        for monitor_name in enabled_monitors:
            # 创建插件实例
            config = self._get_plugin_config(monitor_name)
            plugin = plugin_registry.create_plugin(monitor_name, config)
            
            if plugin:
                self._plugins[monitor_name] = plugin
                success_count += 1
                logger.info(f"已加载监控插件: {monitor_name}")
            else:
                logger.error(f"加载监控插件失败: {monitor_name}")
        
        logger.info(f"成功加载 {success_count}/{len(enabled_monitors)} 个监控插件")
        return success_count > 0
    
    def _get_plugin_config(self, monitor_name: str) -> Dict[str, Any]:
        """获取插件配置"""
        config = {}
        
        if monitor_name == "twitter":
            config = {
                "check_interval": settings.twitter_check_interval,
                "bearer_token": settings.twitter_bearer_token,
            }
        elif monitor_name == "solana":
            config = {
                "check_interval": settings.solana_check_interval,
                "rpc_nodes": settings.solana_rpc_nodes,
                "default_network": settings.solana_default_network,
            }
        
        return config
    
    async def start_all(self) -> bool:
        """
        启动所有插件
        
        Returns:
            是否全部启动成功
        """
        if self._running:
            logger.warning("监控管理器已在运行中")
            return True
        
        if not self._plugins:
            logger.warning("没有可启动的监控插件")
            return False
        
        logger.info("开始启动所有监控插件...")
        
        # 延迟启动
        if settings.monitor_startup_delay > 0:
            logger.info(f"等待 {settings.monitor_startup_delay} 秒后启动监控插件...")
            await asyncio.sleep(settings.monitor_startup_delay)
        
        success_count = 0
        tasks = []
        
        # 并发启动所有插件
        for name, plugin in self._plugins.items():
            task = asyncio.create_task(
                self._start_plugin_with_retry(name, plugin)
            )
            tasks.append(task)
        
        # 等待所有插件启动完成
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                plugin_name = list(self._plugins.keys())[i]
                logger.error(f"启动插件 {plugin_name} 异常: {result}")
            elif result:
                success_count += 1
        
        self._running = success_count > 0
        
        logger.info(f"成功启动 {success_count}/{len(self._plugins)} 个监控插件")
        return self._running
    
    async def _start_plugin_with_retry(self, name: str, plugin: MonitorPlugin, max_retries: int = 3) -> bool:
        """带重试的插件启动"""
        for attempt in range(max_retries):
            try:
                if await plugin.start():
                    return True
                
                if attempt < max_retries - 1:
                    wait_time = 2 ** attempt
                    logger.warning(f"插件 {name} 启动失败，{wait_time}秒后重试...")
                    await asyncio.sleep(wait_time)
                    
            except Exception as e:
                logger.error(f"插件 {name} 启动异常 (尝试 {attempt + 1}): {e}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(2 ** attempt)
        
        logger.error(f"插件 {name} 启动失败，已达最大重试次数")
        return False
    
    async def stop_all(self, timeout: int = None) -> bool:
        """
        停止所有插件
        
        Args:
            timeout: 停止超时时间
            
        Returns:
            是否全部停止成功
        """
        if not self._running:
            return True
        
        timeout = timeout or settings.monitor_graceful_shutdown_timeout
        logger.info(f"开始停止所有监控插件，超时时间: {timeout}秒...")
        
        tasks = []
        for name, plugin in self._plugins.items():
            task = asyncio.create_task(plugin.stop(timeout))
            tasks.append((name, task))
        
        success_count = 0
        
        # 等待所有插件停止
        for name, task in tasks:
            try:
                success = await task
                if success:
                    success_count += 1
                    logger.info(f"插件 {name} 已停止")
                else:
                    logger.error(f"插件 {name} 停止失败")
            except Exception as e:
                logger.error(f"停止插件 {name} 异常: {e}")
        
        self._running = False
        logger.info(f"成功停止 {success_count}/{len(self._plugins)} 个监控插件")
        return success_count == len(self._plugins)
    
    async def restart_plugin(self, name: str) -> bool:
        """重启指定插件"""
        plugin = self._plugins.get(name)
        if not plugin:
            logger.error(f"插件不存在: {name}")
            return False
        
        logger.info(f"重启插件: {name}")
        
        # 先停止
        if not await plugin.stop():
            logger.error(f"停止插件 {name} 失败")
            return False
        
        # 再启动
        return await self._start_plugin_with_retry(name, plugin)
    
    def get_plugin(self, name: str) -> Optional[MonitorPlugin]:
        """获取插件实例"""
        return self._plugins.get(name)
    
    def get_plugin_names(self) -> List[str]:
        """获取所有插件名称"""
        return list(self._plugins.keys())
    
    def get_all_stats(self) -> Dict[str, MonitorStats]:
        """获取所有插件的统计信息"""
        return {name: plugin.get_stats() for name, plugin in self._plugins.items()}
    
    def is_running(self) -> bool:
        """检查管理器是否运行中"""
        return self._running
    
    async def pause_plugin(self, name: str) -> bool:
        """暂停插件"""
        plugin = self._plugins.get(name)
        if not plugin:
            return False
        
        await plugin.pause()
        return True
    
    async def resume_plugin(self, name: str) -> bool:
        """恢复插件"""
        plugin = self._plugins.get(name)
        if not plugin:
            return False
        
        await plugin.resume()
        return True
    
    async def health_check(self) -> Dict[str, Any]:
        """健康检查"""
        total_plugins = len(self._plugins)
        running_plugins = sum(1 for p in self._plugins.values() if p.is_running())
        
        return {
            "manager_running": self._running,
            "total_plugins": total_plugins,
            "running_plugins": running_plugins,
            "health_score": running_plugins / total_plugins if total_plugins > 0 else 0,
            "plugins": {
                name: {
                    "status": plugin.stats.status.value,
                    "success_rate": plugin.stats.success_rate,
                    "uptime_seconds": plugin.stats.uptime_seconds,
                    "total_checks": plugin.stats.total_checks,
                    "last_error": plugin.stats.last_error
                }
                for name, plugin in self._plugins.items()
            }
        }

    @asynccontextmanager
    async def lifecycle(self):
        """监控管理器生命周期上下文管理器"""
        try:
            # 加载插件
            if not await self.load_plugins():
                raise RuntimeError("加载监控插件失败")
            
            # 启动所有插件
            if not await self.start_all():
                raise RuntimeError("启动监控插件失败")
            
            yield self
            
        finally:
            # 停止所有插件
            await self.stop_all()


# 全局监控管理器实例
monitor_manager = MonitorManager()