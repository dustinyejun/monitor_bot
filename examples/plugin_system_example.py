"""
插件化监控系统使用示例
演示如何使用可插拔的监控系统
"""

import asyncio
from src.core.monitor_manager import MonitorManager
from src.config.settings import settings
import src.plugins  # 确保插件被注册


async def basic_example():
    """基本使用示例"""
    print("=== 基本使用示例 ===")
    
    # 创建监控管理器
    manager = MonitorManager()
    
    # 使用生命周期管理器
    async with manager.lifecycle() as mgr:
        print("监控系统已启动")
        
        # 获取所有插件状态
        stats = mgr.get_all_stats()
        for name, stat in stats.items():
            print(f"插件 {name}: {stat.status.value}")
        
        # 等待一段时间观察运行情况
        print("运行10秒...")
        await asyncio.sleep(10)
        
        # 获取健康检查
        health = await mgr.health_check()
        print(f"健康评分: {health['health_score']:.2f}")
        print(f"运行中插件: {health['running_plugins']}/{health['total_plugins']}")
        
    print("监控系统已停止")


async def manual_control_example():
    """手动控制示例"""
    print("\n=== 手动控制示例 ===")
    
    manager = MonitorManager()
    
    # 手动加载插件
    print("加载插件...")
    await manager.load_plugins()
    
    plugins = manager.get_plugin_names()
    print(f"已加载插件: {plugins}")
    
    # 启动所有插件
    print("启动所有插件...")
    await manager.start_all()
    
    # 暂停某个插件
    if "twitter" in plugins:
        print("暂停Twitter插件...")
        await manager.pause_plugin("twitter")
        
        # 等待5秒
        await asyncio.sleep(5)
        
        print("恢复Twitter插件...")
        await manager.resume_plugin("twitter")
    
    # 重启某个插件
    if "solana" in plugins:
        print("重启Solana插件...")
        await manager.restart_plugin("solana")
    
    # 获取插件详细信息
    for plugin_name in plugins:
        plugin = manager.get_plugin(plugin_name)
        if hasattr(plugin, 'get_plugin_info'):
            info = plugin.get_plugin_info()
            print(f"插件 {plugin_name} 信息: v{info['version']} - {info['description']}")
    
    # 停止所有插件
    print("停止所有插件...")
    await manager.stop_all()


async def configuration_example():
    """配置示例"""
    print("\n=== 配置示例 ===")
    
    print("当前配置:")
    print(f"  启用的监控: {settings.get_enabled_monitors()}")
    print(f"  Twitter启用: {settings.is_monitor_enabled('twitter')}")
    print(f"  Solana启用: {settings.is_monitor_enabled('solana')}")
    print(f"  启动延迟: {settings.monitor_startup_delay}秒")
    print(f"  关闭超时: {settings.monitor_graceful_shutdown_timeout}秒")
    
    # 演示动态配置检查
    print("\n动态配置检查:")
    for monitor in ['twitter', 'solana', 'ethereum']:  # ethereum不存在
        enabled = settings.is_monitor_enabled(monitor)
        print(f"  {monitor}: {'启用' if enabled else '禁用'}")


def create_custom_plugin_example():
    """创建自定义插件示例"""
    print("\n=== 自定义插件示例 ===")
    
    from src.core.monitor_plugin import MonitorPlugin, plugin_registry
    
    class CustomMonitorPlugin(MonitorPlugin):
        """自定义监控插件示例"""
        
        @property
        def check_interval(self) -> int:
            return self.get_config("interval", 60)
        
        async def initialize(self) -> bool:
            print(f"初始化自定义插件: {self.name}")
            # 这里添加初始化逻辑
            return True
        
        async def check(self) -> bool:
            print(f"执行自定义检查: {self.name}")
            # 这里添加检查逻辑
            return True
        
        async def cleanup(self):
            print(f"清理自定义插件: {self.name}")
            # 这里添加清理逻辑
    
    # 注册自定义插件
    plugin_registry.register("custom", CustomMonitorPlugin)
    
    # 创建插件实例
    custom_plugin = plugin_registry.create_plugin("custom", {
        "interval": 30,
        "custom_param": "test_value"
    })
    
    print(f"创建自定义插件: {custom_plugin.name}")
    print(f"检查间隔: {custom_plugin.check_interval}秒")
    print(f"自定义参数: {custom_plugin.get_config('custom_param')}")


async def error_handling_example():
    """错误处理示例"""
    print("\n=== 错误处理示例 ===")
    
    from src.core.monitor_plugin import plugin_registry
    
    # 尝试创建不存在的插件
    invalid_plugin = plugin_registry.create_plugin("nonexistent")
    print(f"创建不存在的插件结果: {invalid_plugin}")
    
    # 创建配置不完整的插件
    twitter_plugin = plugin_registry.create_plugin("twitter", {})
    if twitter_plugin:
        print("尝试初始化配置不完整的Twitter插件...")
        success = await twitter_plugin.initialize()
        print(f"初始化结果: {success}")
        if not success:
            print("初始化失败，这是预期的，因为缺少bearer_token")


async def monitoring_stats_example():
    """监控统计示例"""
    print("\n=== 监控统计示例 ===")
    
    manager = MonitorManager()
    
    # 加载和启动插件
    await manager.load_plugins()
    await manager.start_all()
    
    # 运行一段时间收集统计数据
    print("运行15秒收集统计数据...")
    await asyncio.sleep(15)
    
    # 显示统计信息
    all_stats = manager.get_all_stats()
    
    print("插件统计信息:")
    for name, stats in all_stats.items():
        print(f"  {name}:")
        print(f"    状态: {stats.status.value}")
        print(f"    总检查次数: {stats.total_checks}")
        print(f"    成功次数: {stats.successful_checks}")
        print(f"    失败次数: {stats.failed_checks}")
        print(f"    成功率: {stats.success_rate:.2%}")
        print(f"    运行时间: {stats.uptime_seconds}秒")
        if stats.last_error:
            print(f"    最后错误: {stats.last_error}")
    
    # 健康检查
    health = await manager.health_check()
    print(f"\n系统健康状态:")
    print(f"  总体健康评分: {health['health_score']:.2%}")
    print(f"  管理器运行状态: {health['manager_running']}")
    print(f"  插件状态: {health['running_plugins']}/{health['total_plugins']}")
    
    # 停止管理器
    await manager.stop_all()


async def main():
    """主函数"""
    print("插件化监控系统示例")
    print("=" * 50)
    
    try:
        # 基本示例
        await basic_example()
        
        # 手动控制示例
        await manual_control_example()
        
        # 配置示例
        await configuration_example()
        
        # 自定义插件示例
        create_custom_plugin_example()
        
        # 错误处理示例
        await error_handling_example()
        
        # 监控统计示例
        await monitoring_stats_example()
        
    except Exception as e:
        print(f"示例运行出错: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())