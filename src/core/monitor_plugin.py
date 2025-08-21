"""
监控插件基类和接口定义
提供可插拔的监控系统架构
"""

import asyncio
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Dict, Any, Optional, List

from ..utils.logger import logger


class MonitorStatus(Enum):
    """监控状态枚举"""
    STOPPED = "stopped"
    STARTING = "starting"
    RUNNING = "running"
    PAUSED = "paused"
    STOPPING = "stopping"
    ERROR = "error"


@dataclass
class MonitorStats:
    """监控统计信息"""
    name: str
    status: MonitorStatus
    start_time: Optional[datetime] = None
    last_check_time: Optional[datetime] = None
    total_checks: int = 0
    successful_checks: int = 0
    failed_checks: int = 0
    error_count: int = 0
    last_error: Optional[str] = None
    
    @property
    def success_rate(self) -> float:
        """成功率"""
        if self.total_checks == 0:
            return 0.0
        return self.successful_checks / self.total_checks
    
    @property
    def uptime_seconds(self) -> int:
        """运行时间（秒）"""
        if not self.start_time:
            return 0
        return int((datetime.now() - self.start_time).total_seconds())


class MonitorPlugin(ABC):
    """监控插件基类"""
    
    def __init__(self, name: str, config: Dict[str, Any] = None):
        """
        初始化监控插件
        
        Args:
            name: 插件名称
            config: 插件配置
        """
        self.name = name
        self.config = config or {}
        self.stats = MonitorStats(name=name, status=MonitorStatus.STOPPED)
        self._task: Optional[asyncio.Task] = None
        self._stop_event = asyncio.Event()
        
    @abstractmethod
    async def initialize(self) -> bool:
        """
        初始化插件
        
        Returns:
            是否初始化成功
        """
        pass
    
    @abstractmethod
    async def check(self) -> bool:
        """
        执行一次监控检查
        
        Returns:
            检查是否成功
        """
        pass
    
    @abstractmethod 
    async def cleanup(self):
        """清理资源"""
        pass
    
    @property
    @abstractmethod
    def check_interval(self) -> int:
        """检查间隔（秒）"""
        pass
    
    def get_config(self, key: str, default: Any = None) -> Any:
        """获取配置值"""
        return self.config.get(key, default)
    
    async def start(self) -> bool:
        """
        启动监控插件
        
        Returns:
            是否启动成功
        """
        if self._task and not self._task.done():
            logger.warning(f"监控插件 {self.name} 已在运行中")
            return True
            
        logger.info(f"启动监控插件: {self.name}")
        self.stats.status = MonitorStatus.STARTING
        
        try:
            # 初始化插件
            if not await self.initialize():
                logger.error(f"监控插件 {self.name} 初始化失败")
                self.stats.status = MonitorStatus.ERROR
                return False
            
            # 重置停止事件
            self._stop_event.clear()
            
            # 启动监控任务
            self._task = asyncio.create_task(self._run_monitor())
            self.stats.status = MonitorStatus.RUNNING
            self.stats.start_time = datetime.now()
            
            logger.info(f"监控插件 {self.name} 启动成功")
            return True
            
        except Exception as e:
            logger.error(f"启动监控插件 {self.name} 失败: {str(e)}")
            self.stats.status = MonitorStatus.ERROR
            self.stats.last_error = str(e)
            return False
    
    async def stop(self, timeout: int = 30) -> bool:
        """
        停止监控插件
        
        Args:
            timeout: 停止超时时间（秒）
            
        Returns:
            是否停止成功
        """
        if not self._task or self._task.done():
            self.stats.status = MonitorStatus.STOPPED
            return True
            
        logger.info(f"停止监控插件: {self.name}")
        self.stats.status = MonitorStatus.STOPPING
        
        try:
            # 设置停止事件
            self._stop_event.set()
            
            # 等待任务完成
            await asyncio.wait_for(self._task, timeout=timeout)
            
            # 清理资源
            await self.cleanup()
            
            self.stats.status = MonitorStatus.STOPPED
            logger.info(f"监控插件 {self.name} 已停止")
            return True
            
        except asyncio.TimeoutError:
            logger.error(f"监控插件 {self.name} 停止超时，强制取消任务")
            self._task.cancel()
            self.stats.status = MonitorStatus.ERROR
            return False
            
        except Exception as e:
            logger.error(f"停止监控插件 {self.name} 失败: {str(e)}")
            self.stats.status = MonitorStatus.ERROR
            self.stats.last_error = str(e)
            return False
    
    async def pause(self):
        """暂停监控"""
        if self.stats.status == MonitorStatus.RUNNING:
            self.stats.status = MonitorStatus.PAUSED
            logger.info(f"监控插件 {self.name} 已暂停")
    
    async def resume(self):
        """恢复监控"""
        if self.stats.status == MonitorStatus.PAUSED:
            self.stats.status = MonitorStatus.RUNNING
            logger.info(f"监控插件 {self.name} 已恢复")
    
    def is_running(self) -> bool:
        """检查是否正在运行"""
        return self.stats.status == MonitorStatus.RUNNING
    
    def get_stats(self) -> MonitorStats:
        """获取统计信息"""
        return self.stats
    
    async def _run_monitor(self):
        """运行监控循环"""
        logger.info(f"监控插件 {self.name} 开始运行循环，间隔: {self.check_interval}秒")
        
        while not self._stop_event.is_set():
            try:
                # 跳过暂停状态
                if self.stats.status == MonitorStatus.PAUSED:
                    await asyncio.sleep(1)
                    continue
                
                # 执行检查
                self.stats.total_checks += 1
                self.stats.last_check_time = datetime.now()
                
                success = await self.check()
                
                if success:
                    self.stats.successful_checks += 1
                else:
                    self.stats.failed_checks += 1
                    
            except Exception as e:
                logger.error(f"监控插件 {self.name} 检查出错: {str(e)}")
                self.stats.error_count += 1
                self.stats.failed_checks += 1
                self.stats.last_error = str(e)
            
            # 等待下次检查
            try:
                await asyncio.wait_for(
                    self._stop_event.wait(), 
                    timeout=self.check_interval
                )
                break  # 收到停止信号
            except asyncio.TimeoutError:
                continue  # 正常超时，继续下次循环
        
        logger.info(f"监控插件 {self.name} 监控循环已结束")


class MonitorPluginRegistry:
    """监控插件注册表"""
    
    def __init__(self):
        self._plugins: Dict[str, type] = {}
    
    def register(self, name: str, plugin_class: type):
        """注册插件类"""
        if not issubclass(plugin_class, MonitorPlugin):
            raise ValueError(f"插件类必须继承自MonitorPlugin: {plugin_class}")
        
        self._plugins[name.lower()] = plugin_class
        logger.info(f"已注册监控插件: {name}")
    
    def get_plugin_class(self, name: str) -> Optional[type]:
        """获取插件类"""
        return self._plugins.get(name.lower())
    
    def get_available_plugins(self) -> List[str]:
        """获取可用的插件列表"""
        return list(self._plugins.keys())
    
    def create_plugin(self, name: str, config: Dict[str, Any] = None) -> Optional[MonitorPlugin]:
        """创建插件实例"""
        plugin_class = self.get_plugin_class(name)
        if not plugin_class:
            logger.error(f"未找到监控插件: {name}")
            return None
        
        try:
            return plugin_class(name, config)
        except Exception as e:
            logger.error(f"创建监控插件 {name} 失败: {str(e)}")
            return None


# 全局插件注册表
plugin_registry = MonitorPluginRegistry()