# 通知系统文档

## 概述

通知系统是监控机器人的核心组件之一，负责将监控到的重要事件通过各种渠道（企业微信、邮件、短信等）及时推送给用户。系统采用基于规则的触发机制，支持模板化消息、去重、限流等高级功能。

## 系统架构

```
通知系统架构
├── 通知服务 (NotificationService)
│   ├── 企业微信发送
│   ├── 邮件发送 (待实现)
│   └── 短信发送 (待实现)
├── 模板管理 (NotificationTemplateService)
│   ├── 模板CRUD
│   ├── 规则管理
│   └── 变量渲染
├── 通知引擎 (NotificationEngine)
│   ├── 规则评估
│   ├── 条件匹配
│   └── 自动触发
└── 限流去重 (RateLimiter + DeduplicationService)
    ├── 内存缓存
    ├── 数据库检查
    └── 统计监控
```

## 核心功能

### 1. 通知发送

支持多种渠道的通知发送：

```python
# 直接发送通知
from src.services.notification_service import notification_service
from src.schemas.notification import NotificationCreate

notification = NotificationCreate(
    type="twitter",
    title="🚨 CA地址推文提醒",
    content="发现重要推文...",
    is_urgent=True,
    channel="wechat"
)

success = await notification_service.send_notification(notification)
```

### 2. 模板化通知

使用预定义模板发送通知：

```python
# 使用模板发送
from src.schemas.notification import NotificationTriggerRequest

trigger = NotificationTriggerRequest(
    template_name="twitter_ca_alert",
    variables={
        "username": "elonmusk",
        "content": "New token CA: 0x123...",
        "ca_addresses": "0x123..."
    }
)

success = await notification_service.send_by_template(trigger)
```

### 3. 规则引擎

基于条件自动触发通知：

```python
# 规则示例
{
    "and": [
        {"field": "amount_usd", "operator": "gt", "value": 10000},
        {"field": "transaction_type", "operator": "eq", "value": "swap"}
    ]
}
```

支持的操作符：
- 数值比较: `gt`, `gte`, `lt`, `lte`, `eq`, `ne`
- 字符串匹配: `contains`, `startswith`, `endswith`, `in`, `not_in`
- 正则表达式: `regex`
- 时间比较: `within_minutes`, `within_hours`

## 数据模型

### 通知表 (notifications)

| 字段 | 类型 | 说明 |
|------|------|------|
| id | Integer | 主键 |
| type | String | 通知类型 |
| title | String | 通知标题 |
| content | Text | 通知内容 |
| status | String | 状态: pending/sent/failed |
| is_urgent | Boolean | 是否紧急 |
| channel | String | 通知渠道 |
| dedup_key | String | 去重键 |
| data | JSON | 扩展数据 |
| sent_at | DateTime | 发送时间 |
| retry_count | Integer | 重试次数 |

### 通知模板表 (notification_templates)

| 字段 | 类型 | 说明 |
|------|------|------|
| id | Integer | 主键 |
| name | String | 模板名称 |
| type | String | 通知类型 |
| title_template | String | 标题模板 |
| content_template | Text | 内容模板 |
| is_active | Boolean | 是否启用 |
| dedup_enabled | Boolean | 是否启用去重 |
| variables | JSON | 模板变量说明 |

### 通知规则表 (notification_rules)

| 字段 | 类型 | 说明 |
|------|------|------|
| id | Integer | 主键 |
| name | String | 规则名称 |
| type | String | 监控类型 |
| conditions | JSON | 触发条件 |
| template_name | String | 使用的模板 |
| priority | Integer | 优先级 |
| rate_limit_enabled | Boolean | 是否启用限流 |
| rate_limit_count | Integer | 限流次数 |

## API接口

### 基础通知接口

```bash
# 发送通知
POST /api/notification/send
{
    "type": "system",
    "title": "系统通知",
    "content": "内容",
    "channel": "wechat"
}

# 使用模板发送
POST /api/notification/send-by-template
{
    "template_name": "twitter_ca_alert",
    "variables": {"username": "test"}
}

# 获取通知列表
GET /api/notification/list?type=twitter&limit=20

# 获取通知统计
GET /api/notification/stats
```

### 模板管理接口

```bash
# 创建模板
POST /api/notification/templates
{
    "name": "custom_template",
    "type": "twitter",
    "title_template": "标题: {title}",
    "content_template": "内容: {content}"
}

# 获取模板列表
GET /api/notification/templates?type=twitter

# 更新模板
PUT /api/notification/templates/{id}
```

### 规则管理接口

```bash
# 创建规则
POST /api/notification/rules
{
    "name": "large_transaction",
    "type": "solana",
    "conditions": {"field": "amount_usd", "operator": "gt", "value": 10000},
    "template_name": "solana_large_transaction"
}

# 获取规则列表
GET /api/notification/rules?type=solana
```

## 默认模板和规则

### 默认模板

1. **twitter_ca_alert** - Twitter CA地址推文提醒
2. **solana_large_transaction** - Solana大额交易提醒
3. **system_status_alert** - 系统状态提醒

### 默认规则

1. **twitter_ca_detection** - 检测包含CA地址的推文
2. **solana_large_transaction** - 检测大额Solana交易

## 配置说明

在 `.env` 文件中配置企业微信Webhook：

```env
# 企业微信配置
WECHAT_WEBHOOK_URL=https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=your_key
```

## 高级功能

### 去重机制

- **时间窗口去重**: 在指定时间内相同去重键的通知只发送一次
- **内存缓存**: 快速去重检查，提高性能
- **数据库持久化**: 确保去重的准确性

### 限流机制

- **规则级限流**: 每个规则可以设置独立的限流参数
- **时间窗口限流**: 在指定时间窗口内限制通知数量
- **多级缓存**: 内存+数据库双重检查

### 错误处理

- **重试机制**: 失败的通知自动重试，最多3次
- **错误记录**: 详细记录发送失败的原因
- **监控统计**: 提供发送成功率等统计信息

## 监控插件集成

通知系统已集成到监控插件中：

### Twitter监控集成

```python
# 在TwitterMonitorPlugin中
async def _trigger_notifications(self, user, ca_tweets):
    for analysis in ca_tweets:
        notification_data = {
            "username": user.username,
            "content": analysis.content,
            "ca_addresses": ", ".join(analysis.ca_addresses),
            # ...
        }
        await notification_engine.check_twitter_rules(notification_data)
```

### Solana监控集成

```python
# 在SolanaMonitorPlugin中
async def _trigger_notifications(self, wallet, transactions):
    for analysis in transactions:
        notification_data = {
            "wallet_address": wallet.address,
            "transaction_type": analysis.transaction_type.value,
            "amount_usd": float(analysis.total_value_usd),
            # ...
        }
        await notification_engine.check_solana_rules(notification_data)
```

## 测试

运行通知系统测试：

```bash
# 运行单元测试
uv run pytest tests/test_notification_services.py

# 测试通知发送
curl -X POST "http://localhost:8000/api/notification/test"

# 测试模板通知
curl -X POST "http://localhost:8000/api/notification/test-template"
```

## 初始化

系统首次运行时需要初始化默认模板和规则：

```bash
# 调用初始化接口
curl -X POST "http://localhost:8000/api/notification/initialize"
```

或在代码中调用：

```python
from src.services.notification_template_service import init_default_templates
from src.services.notification_engine import init_default_rules

# 初始化默认模板
init_default_templates()

# 初始化默认规则
init_default_rules()
```

## 扩展开发

### 添加新的通知渠道

1. 在 `NotificationService` 中添加新的发送方法
2. 更新 `NotificationChannel` 枚举
3. 实现具体的发送逻辑

### 添加新的操作符

1. 在 `NotificationEngine._init_condition_handlers()` 中添加新操作符
2. 实现对应的处理函数
3. 更新文档说明

### 自定义模板变量

1. 在模板中使用 `{variable_name}` 语法
2. 在 `variables` 字段中记录变量说明
3. 在触发通知时提供变量值

## 注意事项

1. **企业微信限制**: 企业微信对消息发送频率有限制，建议合理设置限流参数
2. **数据库性能**: 大量通知会影响数据库性能，建议定期清理历史数据
3. **内存使用**: 去重和限流缓存会占用内存，建议监控内存使用情况
4. **网络超时**: 发送通知时可能遇到网络超时，系统会自动重试

## 故障排除

### 通知发送失败

1. 检查企业微信Webhook URL是否正确
2. 检查网络连接是否正常
3. 查看错误日志确定具体原因
4. 使用测试接口验证配置

### 规则不触发

1. 检查规则是否启用
2. 验证条件表达式是否正确
3. 检查数据格式是否匹配
4. 查看引擎处理日志

### 通知重复发送

1. 检查去重配置是否正确
2. 确认去重键生成逻辑
3. 验证时间窗口设置
4. 清理去重缓存重新测试