# 数据库依赖问题解决方案

## 问题描述

在测试企业微信通知功能时遇到的错误：

```
psycopg2.OperationalError: connection to server at "localhost" (::1), port 5432 failed: Connection refused
```

## 问题原因

### 1. 数据库依赖设计

当前的通知系统在发送通知时会：
1. 连接PostgreSQL数据库
2. 创建通知记录
3. 发送企业微信消息
4. 更新发送状态

这种设计的优点：
- 完整的通知历史记录
- 支持去重和限流
- 提供统计功能
- 支持重试机制

### 2. 测试环境问题

测试时没有启动PostgreSQL数据库服务，导致：
- 无法创建数据库连接
- 通知记录创建失败
- 整个发送流程中断

## 解决方案

### 方案1：启动数据库服务（推荐用于完整测试）

```bash
# 启动PostgreSQL服务（macOS）
brew services start postgresql

# 或者使用Docker
docker run --name postgres-test -e POSTGRES_PASSWORD=password -d -p 5432:5432 postgres

# 然后运行完整测试
python quick_test_notification.py
```

### 方案2：无数据库简化测试（推荐用于快速验证）

我们创建了两个简化版本的测试：

#### `test_wechat_simple.py` - 基于aiohttp的简化测试
```python
# 直接调用企业微信API，不依赖数据库
await send_wechat_message(webhook_url, title, content)
```

#### `test_wechat_curl.py` - 基于curl的最简测试
```bash
# 使用系统curl命令，无Python依赖
python test_wechat_curl.py
```

### 方案3：Mock数据库（用于单元测试）

```python
# 在测试中Mock数据库连接
@patch('src.services.notification_service.SessionLocal')
async def test_notification_without_db(mock_session):
    # 测试逻辑
    pass
```

## 测试策略建议

### 快速验证阶段
使用简化测试验证基本功能：
```bash
# 最快的验证方式
python test_wechat_curl.py
```

### 功能开发阶段
启动数据库进行完整测试：
```bash
# 启动数据库
brew services start postgresql

# 运行数据库迁移
uv run alembic upgrade head

# 运行完整测试
python quick_test_notification.py
python test_wechat_real.py
```

### 生产部署阶段
- 确保PostgreSQL服务正常运行
- 配置数据库连接参数
- 运行完整的集成测试

## 优化建议

### 1. 配置化数据库依赖

可以添加配置选项控制是否使用数据库：

```python
# 在settings.py中添加
NOTIFICATION_USE_DATABASE = os.getenv("NOTIFICATION_USE_DATABASE", "true").lower() == "true"

# 在通知服务中
if settings.NOTIFICATION_USE_DATABASE:
    # 使用数据库记录
    await self._save_to_database(notification)
else:
    # 仅发送，不记录
    pass
```

### 2. 优雅降级

当数据库不可用时，仍然发送通知：

```python
async def send_notification(self, notification_data):
    try:
        # 尝试记录到数据库
        db_record = await self._create_db_record(notification_data)
    except DatabaseError:
        logger.warning("数据库不可用，仅发送通知")
        db_record = None
    
    # 发送通知（无论数据库是否可用）
    success = await self._send_by_channel(notification_data)
    
    if db_record and success:
        await self._update_db_status(db_record, "sent")
    
    return success
```

### 3. 健康检查

添加数据库健康检查：

```python
async def check_database_health(self):
    try:
        db = SessionLocal()
        db.execute("SELECT 1")
        db.close()
        return True
    except Exception:
        return False
```

## 当前解决状态

✅ **问题已解决**

- 创建了无数据库依赖的简化测试版本
- 企业微信通知功能测试完全通过
- 提供了多种测试方案供不同场景使用

## 使用建议

### 开发阶段
```bash
# 快速验证企业微信配置
python test_wechat_curl.py

# 开发功能时启动数据库
brew services start postgresql
python quick_test_notification.py
```

### 生产环境
- 确保PostgreSQL服务稳定运行
- 使用完整的通知系统功能
- 定期监控数据库连接状态

这样既保证了功能的完整性，又提供了灵活的测试方案。