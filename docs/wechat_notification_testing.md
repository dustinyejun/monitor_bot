# 企业微信通知测试指南

## 概述

本文档介绍如何测试企业微信通知功能，包括单元测试、集成测试和真实API测试。

## 前置准备

### 1. 获取企业微信机器人Webhook URL

1. 在企业微信群中添加机器人：
   - 打开企业微信群聊
   - 点击右上角"..."菜单
   - 选择"添加群机器人"
   - 创建机器人并复制Webhook URL

2. Webhook URL格式示例：
   ```
   https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=693axxx6-7aoc-4bc4-97a0-0ec2sifa5aaa
   ```

### 2. 配置环境变量

在 `.env` 文件中添加：
```env
WECHAT_WEBHOOK_URL=https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=your_actual_key
```

## 测试方式

### 1. 快速测试（推荐）

最简单的测试方式，验证基本功能：

```bash
# 运行快速测试
python quick_test_notification.py
```

这将发送一条测试通知到您的企业微信群。

### 2. 完整功能测试

测试所有通知功能，包括模板、去重等：

```bash
# 运行完整测试
python test_wechat_real.py
```

测试内容包括：
- 基础通知发送
- 紧急通知发送
- 模板通知发送
- Solana交易通知
- 去重功能测试
- 统计信息获取

### 3. 单元测试

运行自动化单元测试：

```bash
# 运行所有通知相关测试
uv run pytest tests/test_wechat_notification.py -v

# 运行包括真实API的测试（需要有效的Webhook URL）
uv run pytest tests/test_wechat_notification.py --run-real-api -v

# 只运行Mock测试（不需要真实API）
uv run pytest tests/test_wechat_notification.py -v -m "not real_api"
```

### 4. API接口测试

通过HTTP API测试：

```bash
# 测试基础通知发送
curl -X POST "http://localhost:8000/api/notification/test" \
  -H "Content-Type: application/json"

# 测试模板通知发送
curl -X POST "http://localhost:8000/api/notification/test-template" \
  -H "Content-Type: application/json"

# 获取通知统计
curl -X GET "http://localhost:8000/api/notification/stats"
```

## 测试用例说明

### 1. 基础通知测试

测试最基本的通知发送功能：

```python
notification = NotificationCreate(
    type=NotificationType.SYSTEM,
    title="🧪 系统测试",
    content="这是一条测试通知",
    channel=NotificationChannel.WECHAT
)
```

**预期结果**: 企业微信群收到Markdown格式的系统通知

### 2. 紧急通知测试

测试紧急通知的特殊格式：

```python
notification = NotificationCreate(
    type=NotificationType.TWITTER,
    title="🚨 CA地址推文提醒", 
    content="发现重要推文...",
    is_urgent=True,
    channel=NotificationChannel.WECHAT
)
```

**预期结果**: 消息标题带有🚨标识，格式更醒目

### 3. 模板通知测试

测试使用预定义模板发送通知：

```python
template_request = NotificationTriggerRequest(
    template_name="system_status_alert",
    variables={
        "component": "Twitter监控插件",
        "status": "运行正常",
        "message": "系统正常运行",
        "timestamp": "2025-08-20 10:30:00"
    }
)
```

**预期结果**: 根据模板格式化的通知，变量被正确替换

### 4. 去重功能测试

测试相同去重键的通知去重：

```python
# 发送两条相同dedup_key的通知
notification1 = NotificationCreate(..., dedup_key="test_key")
notification2 = NotificationCreate(..., dedup_key="test_key")
```

**预期结果**: 第二条通知被去重，不会实际发送

### 5. 错误处理测试

测试各种错误情况的处理：
- 无效的Webhook URL
- 网络连接失败
- 企业微信API错误返回
- HTTP超时

## 测试结果验证

### 成功标志

1. **控制台输出**: 看到 "✅ 通知发送成功" 消息
2. **企业微信消息**: 群聊中收到格式化的通知消息
3. **数据库记录**: 通知记录状态为 "sent"
4. **统计信息**: 发送成功计数增加

### 失败排查

1. **检查配置**:
   ```bash
   # 验证环境变量
   echo $WECHAT_WEBHOOK_URL
   ```

2. **检查网络连接**:
   ```bash
   # 测试Webhook URL可访问性
   curl -X POST "$WECHAT_WEBHOOK_URL" \
     -H "Content-Type: application/json" \
     -d '{"msgtype":"text","text":{"content":"连接测试"}}'
   ```

3. **查看日志**:
   检查应用日志中的错误信息

4. **常见错误**:
   - `93000`: 无效的webhook url
   - `93004`: 机器人被移除
   - `93008`: 消息内容超长
   - `网络超时`: 检查网络连接

## 消息格式示例

### 基础通知格式
```markdown
## 🧪 系统测试

这是一条测试通知

⏰ 2025-08-20 10:30:00
```

### 紧急通知格式
```markdown
## 🚨 CA地址推文提醒

### 📱 用户: elonmusk
**推文内容**: 发现新代币合约

**CA地址**: `0x1234567890abcdef`

**推文链接**: https://twitter.com/elonmusk/status/123456

**发布时间**: 2025-08-20 10:30:00

⏰ 2025-08-20 10:30:00
```

### 系统状态通知格式
```markdown
## ⚠️ 系统状态提醒

### ⚠️ 系统状态异常
**组件**: Twitter监控插件
**状态**: 运行正常
**详细信息**: 系统正常运行

**时间**: 2025-08-20 10:30:00

⏰ 2025-08-20 10:30:00
```

## 性能测试

### 并发测试

测试同时发送多条通知的性能：

```bash
# 运行性能测试
uv run pytest tests/test_wechat_notification.py::TestWeChatPerformance::test_concurrent_notifications -v
```

### 限流测试

测试通知限流功能：

```python
# 快速发送多条通知，验证限流机制
for i in range(20):
    await notification_service.send_notification(notification)
```

## 最佳实践

### 1. 测试环境隔离

- 使用独立的测试群进行测试
- 测试通知添加明显的测试标识
- 避免在生产群中进行测试

### 2. 批量测试

- 测试间隔适当延时（1-2秒）
- 避免触发企业微信的频率限制
- 使用去重键避免重复通知

### 3. 错误处理

- 总是检查返回结果
- 记录详细的错误日志
- 实现重试机制

### 4. 监控和统计

- 定期检查发送成功率
- 监控通知响应时间
- 分析失败原因并优化

## 故障排除清单

1. ✅ 检查 `.env` 文件中的 `WECHAT_WEBHOOK_URL` 配置
2. ✅ 验证 Webhook URL 的有效性
3. ✅ 确认网络连接正常
4. ✅ 检查企业微信机器人状态
5. ✅ 查看应用日志错误信息
6. ✅ 验证消息内容格式
7. ✅ 检查数据库连接
8. ✅ 确认所需的Python包已安装

## 联系支持

如果测试过程中遇到问题：

1. 查看本文档的故障排除部分
2. 检查项目的GitHub Issues
3. 查看企业微信开发者文档
4. 联系项目维护者