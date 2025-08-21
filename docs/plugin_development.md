# 监控插件开发指南

## 概述

本系统采用插件化架构，允许通过配置文件灵活启用/禁用不同类型的监控功能。每个监控类型都实现为一个独立的插件，可以独立开发、测试和部署。

## 系统架构

```
监控管理器 (MonitorManager)
├── 插件注册表 (PluginRegistry)  
├── Twitter监控插件 (TwitterMonitorPlugin)
├── Solana监控插件 (SolanaMonitorPlugin)
└── 自定义插件 (CustomPlugin)
```

## 插件基类

所有监控插件都必须继承自 `MonitorPlugin` 基类：

```python
from src.core.monitor_plugin import MonitorPlugin

class YourPlugin(MonitorPlugin):
    @property
    def check_interval(self) -> int:
        """检查间隔（秒）"""
        return self.get_config("check_interval", 60)
    
    async def initialize(self) -> bool:
        """初始化插件，返回是否成功"""
        # 初始化逻辑
        return True
    
    async def check(self) -> bool:
        """执行一次监控检查，返回是否成功"""
        # 检查逻辑
        return True
    
    async def cleanup(self):
        """清理资源"""
        # 清理逻辑
        pass
```

## 插件生命周期

1. **注册阶段**: 插件类注册到全局注册表
2. **创建阶段**: 根据配置创建插件实例
3. **初始化阶段**: 调用 `initialize()` 方法
4. **运行阶段**: 周期性调用 `check()` 方法
5. **停止阶段**: 调用 `cleanup()` 方法清理资源

## 配置系统

### 环境变量配置

在 `.env` 文件中添加插件配置：

```env
# 启用的监控插件列表
ENABLED_MONITORS=twitter,solana,your_plugin

# 插件特定配置
YOUR_PLUGIN_CHECK_INTERVAL=30
YOUR_PLUGIN_CUSTOM_PARAM=value
```

### 配置类更新

在 `src/config/settings.py` 中添加配置字段：

```python
class Settings(BaseSettings):
    # 你的插件配置
    your_plugin_check_interval: int = 30
    your_plugin_custom_param: str = ""
```

### 监控管理器配置

在 `MonitorManager._get_plugin_config()` 中添加配置映射：

```python
def _get_plugin_config(self, monitor_name: str) -> Dict[str, Any]:
    if monitor_name == "your_plugin":
        config = {
            "check_interval": settings.your_plugin_check_interval,
            "custom_param": settings.your_plugin_custom_param,
        }
    return config
```

## 开发步骤

### 1. 创建插件文件

```python
# src/plugins/your_plugin.py
from ..core.monitor_plugin import MonitorPlugin

class YourMonitorPlugin(MonitorPlugin):
    def __init__(self, name: str, config: Dict[str, Any] = None):
        super().__init__(name, config)
        # 初始化插件特定属性
    
    @property
    def check_interval(self) -> int:
        return self.get_config("check_interval", 60)
    
    async def initialize(self) -> bool:
        try:
            # 检查必要配置
            required_param = self.get_config("custom_param")
            if not required_param:
                logger.error("缺少必要配置参数")
                return False
            
            # 初始化客户端、服务等
            # self.client = SomeClient(required_param)
            
            logger.info("插件初始化成功")
            return True
        except Exception as e:
            logger.error(f"插件初始化失败: {e}")
            return False
    
    async def check(self) -> bool:
        try:
            # 执行监控检查逻辑
            # 1. 获取数据
            # 2. 分析数据
            # 3. 处理结果
            # 4. 触发通知（如需要）
            
            logger.debug("监控检查完成")
            return True
        except Exception as e:
            logger.error(f"监控检查失败: {e}")
            return False
    
    async def cleanup(self):
        try:
            # 清理资源
            # if self.client:
            #     await self.client.close()
            
            logger.info("插件资源清理完成")
        except Exception as e:
            logger.error(f"插件清理失败: {e}")
```

### 2. 注册插件

在插件文件末尾注册插件：

```python
from ..core.monitor_plugin import plugin_registry
plugin_registry.register("your_plugin", YourMonitorPlugin)
```

### 3. 更新插件模块

在 `src/plugins/__init__.py` 中添加导入：

```python
from .your_plugin import YourMonitorPlugin

__all__ = [
    "TwitterMonitorPlugin",
    "SolanaMonitorPlugin", 
    "YourMonitorPlugin"
]
```

### 4. 编写测试

创建 `tests/test_your_plugin.py`：

```python
import pytest
from src.plugins.your_plugin import YourMonitorPlugin

class TestYourPlugin:
    @pytest.fixture
    def plugin(self):
        config = {"check_interval": 30, "custom_param": "test"}
        return YourMonitorPlugin("your_plugin", config)
    
    def test_plugin_creation(self, plugin):
        assert plugin.name == "your_plugin"
        assert plugin.check_interval == 30
    
    @pytest.mark.asyncio
    async def test_plugin_lifecycle(self, plugin):
        # 测试初始化
        assert await plugin.initialize()
        
        # 测试检查
        assert await plugin.check()
        
        # 测试清理
        await plugin.cleanup()
```

## 最佳实践

### 1. 错误处理

- 所有异步方法都应该使用 try-except 包装
- 记录详细的错误日志
- 优雅地处理网络超时和API限制

### 2. 配置管理

- 使用 `get_config()` 方法获取配置
- 为所有配置参数提供合理的默认值
- 在初始化时验证必要的配置参数

### 3. 资源管理

- 使用异步上下文管理器管理网络连接
- 在 `cleanup()` 方法中正确释放资源
- 避免资源泄漏

### 4. 日志记录

- 使用结构化日志记录
- 记录关键操作的开始和结束
- 不要记录敏感信息（如API密钥）

### 5. 性能优化

- 避免阻塞操作
- 使用批量操作减少API调用
- 实现合理的重试机制

## 插件扩展功能

### 自定义方法

插件可以提供额外的公共方法：

```python
class YourMonitorPlugin(MonitorPlugin):
    async def get_custom_data(self, param: str):
        """自定义数据获取方法"""
        # 实现逻辑
        return data
    
    def get_plugin_info(self) -> Dict[str, Any]:
        """获取插件详细信息"""
        return {
            "name": self.name,
            "type": "your_monitor",
            "version": "1.0.0",
            "description": "你的插件描述",
            "config": {
                "check_interval": self.check_interval,
                # 其他配置信息
            }
        }
```

### 事件通知

集成通知系统：

```python
async def _trigger_notification(self, data):
    """触发通知"""
    # 发送企业微信消息
    # 发送邮件通知
    # 其他通知方式
    pass
```

## 测试指南

### 单元测试

- 测试插件创建和配置
- 测试初始化逻辑
- 测试检查逻辑
- 测试错误处理

### 集成测试

- 测试与外部API的交互
- 测试完整的监控流程
- 测试资源清理

### Mock测试

```python
@patch('your_plugin.ExternalClient')
async def test_with_mock(self, mock_client, plugin):
    mock_client.return_value.get_data.return_value = test_data
    
    assert await plugin.initialize()
    assert await plugin.check()
```

## 部署和维护

### 配置部署

1. 更新 `.env` 文件
2. 重启监控系统
3. 检查插件状态

### 监控插件健康状态

```python
# 获取插件状态
health = await monitor_manager.health_check()
print(health["plugins"]["your_plugin"])

# 重启有问题的插件
await monitor_manager.restart_plugin("your_plugin")
```

### 性能监控

- 监控检查成功率
- 监控检查耗时
- 监控资源使用情况

## 示例插件

参考现有插件实现：

- `TwitterMonitorPlugin`: 社交媒体监控
- `SolanaMonitorPlugin`: 区块链钱包监控

每个插件都展示了不同的最佳实践和实现模式。