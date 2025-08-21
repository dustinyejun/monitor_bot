# 推特与Solana监控机器人

一个全面的加密货币监控系统，能够监控推特用户的CA地址相关推文，以及Solana钱包的交易活动，并通过企业微信发送通知。

## 🎯 主要功能

### 🔌 插件化监控架构
- **可插拔设计**: 通过配置灵活启用/禁用监控功能
- **独立运行**: 各监控插件独立运行，互不影响
- **统一管理**: 集中管理所有监控插件的生命周期
- **易于扩展**: 快速添加新的监控类型

### 📱 Twitter监控插件
- **智能CA地址识别**: 支持多链地址识别 (Ethereum, BSC, Solana, Polygon等)
- **用户推文监控**: 实时监控指定用户的推文更新
- **内容分析**: 关键词识别、风险评分、置信度计算
- **过滤系统**: 基于置信度和风险评分的智能过滤

### 💰 Solana监控插件
- **钱包交易监控**: 实时监控Solana钱包的所有交易
- **多DEX支持**: 支持Raydium, Jupiter, Orca等主流DEX
- **交易分析**: 自动识别转账、交换、流动性操作等
- **价值计算**: 实时USD价值计算和风险评估

### 🔔 智能通知系统
- **多渠道支持**: 企业微信、邮件、短信等多种通知渠道
- **规则引擎**: 基于条件自动触发通知，支持复杂逻辑判断
- **模板化消息**: 预定义消息模板，支持变量替换
- **智能去重**: 时间窗口去重，避免重复通知
- **限流保护**: 防止通知风暴，支持规则级限流配置
- **重试机制**: 失败通知自动重试，确保消息送达
- **统计监控**: 完整的发送统计和成功率监控

## 🛠️ 技术架构

- **后端框架**: FastAPI
- **插件系统**: 可插拔监控架构
- **数据库**: PostgreSQL + SQLAlchemy ORM
- **任务调度**: 异步任务调度系统
- **HTTP客户端**: aiohttp (异步)
- **数据验证**: Pydantic v2
- **日志系统**: loguru
- **依赖管理**: UV
- **容器化**: Docker + docker-compose

## 🚀 快速开始

### 环境要求

- Python 3.9+
- PostgreSQL 12+
- UV包管理器

### 安装步骤

1. **克隆项目**
```bash
git clone <repository-url>
cd monitor_bot
```

2. **安装依赖**
```bash
uv sync --dev
```

3. **配置环境变量**
```bash
cp .env.example .env
# 编辑.env文件，配置必要的API密钥和数据库连接
```

4. **数据库初始化**
```bash
# 创建数据库迁移
uv run alembic revision --autogenerate -m "Initial migration"

# 执行迁移
uv run alembic upgrade head
```

5. **运行测试**
```bash
# 运行单元测试
uv run pytest

# 测试推特API连接
uv run python tests/test_real_twitter_api.py

# 测试Solana RPC连接
uv run python tests/test_solana_rpc.py
```

### 配置说明

#### 必要配置

```env
# 数据库
DATABASE_URL=postgresql://user:password@localhost:5432/monitor_bot

# Twitter API
TWITTER_BEARER_TOKEN=your_twitter_bearer_token_here

# Solana RPC配置（多节点数组格式）
SOLANA_RPC_MAINNET_URLS=https://api.mainnet-beta.solana.com,https://backup-node.com
SOLANA_RPC_DEVNET_URLS=https://api.devnet.solana.com
SOLANA_DEFAULT_NETWORK=mainnet

# 企业微信
WECHAT_WEBHOOK_URL=https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=your_key

# 监控插件配置
ENABLED_MONITORS=twitter,solana
```

#### 可选配置

```env
# 监控间隔
TWITTER_CHECK_INTERVAL=60
SOLANA_CHECK_INTERVAL=30

# 日志级别
LOG_LEVEL=INFO

# 应用配置
DEBUG=False
```

## 📊 API接口

### 推特监控

```bash
# 添加监控用户
POST /api/twitter/users
{
    "username": "elonmusk",
    "display_name": "Elon Musk"
}

# 获取用户列表
GET /api/twitter/users

# 获取用户推文
GET /api/twitter/users/{username}/tweets

# 获取包含CA地址的推文
GET /api/twitter/ca-tweets
```

### Solana监控

```bash
# 添加监控钱包
POST /api/solana/wallets
{
    "address": "wallet_address_here",
    "label": "My Wallet",
    "exclude_tokens": ["token1", "token2"]
}

# 获取钱包列表
GET /api/solana/wallets

# 获取钱包交易
GET /api/solana/wallets/{address}/transactions

# 获取钱包余额
GET /api/solana/wallets/{address}/balance
```

### 通知系统

```bash
# 发送通知
POST /api/notification/send
{
    "type": "system",
    "title": "系统通知",
    "content": "通知内容"
}

# 使用模板发送
POST /api/notification/send-by-template
{
    "template_name": "twitter_ca_alert",
    "variables": {"username": "test"}
}

# 获取通知统计
GET /api/notification/stats

# 管理通知模板
GET /api/notification/templates
POST /api/notification/templates

# 管理通知规则
GET /api/notification/rules
POST /api/notification/rules
```

### 系统监控

```bash
# 获取系统状态
GET /api/system/health

# 获取统计信息
GET /api/system/stats

# 获取未处理事件
GET /api/system/pending-events
```

## 🧪 测试

项目包含完整的测试套件，覆盖所有核心功能：

```bash
# 运行所有测试
uv run pytest

# 运行特定测试
uv run pytest tests/test_twitter_services.py
uv run pytest tests/test_solana_services.py

# 运行真实API测试
uv run python tests/test_real_twitter_api.py
```

### 测试覆盖

- **推特服务**: API客户端、内容分析、监控服务
- **Solana服务**: RPC客户端、交易分析、钱包监控
- **通知系统**: 通知发送、模板管理、规则引擎、限流去重
- **插件系统**: 插件生命周期、监控管理器、状态管理
- **数据模型**: 数据库模型和Pydantic schemas
- **集成测试**: 端到端工作流测试

## 📁 项目结构

```
monitor_bot/
├── src/
│   ├── config/          # 配置文件
│   │   ├── settings.py  # 环境配置
│   │   └── database.py  # 数据库配置
│   ├── models/          # 数据库模型
│   │   ├── twitter.py   # 推特相关模型
│   │   ├── solana.py    # Solana相关模型
│   │   └── notification.py # 通知相关模型
│   ├── schemas/         # Pydantic模式
│   ├── core/            # 核心组件
│   │   ├── monitor_plugin.py    # 监控插件基类
│   │   └── monitor_manager.py   # 监控管理器
│   ├── plugins/         # 监控插件
│   │   ├── twitter_monitor_plugin.py  # Twitter监控插件
│   │   └── solana_monitor_plugin.py   # Solana监控插件
│   ├── services/        # 核心业务服务
│   │   ├── twitter_*         # Twitter服务组件
│   │   ├── solana_*          # Solana服务组件
│   │   ├── notification_*    # 通知服务组件
│   │   └── rate_limiter.py   # 限流去重服务
│   ├── api/             # FastAPI路由
│   └── utils/           # 工具函数
├── tests/               # 测试文件
├── migrations/          # 数据库迁移
├── examples/            # 使用示例
├── docker/             # Docker配置
└── docs/               # 文档
```

## 🔧 开发指南

### 添加新的监控目标

1. **创建数据模型**
```python
# src/models/new_service.py
class NewServiceModel(BaseModel):
    address = Column(String, unique=True)
    label = Column(String)
    # ... 其他字段
```

2. **实现客户端**
```python
# src/services/new_service_client.py
class NewServiceClient:
    async def get_data(self, address: str):
        # 实现数据获取逻辑
        pass
```

3. **添加分析器**
```python
# src/services/new_service_analyzer.py
class NewServiceAnalyzer:
    async def analyze_data(self, data):
        # 实现分析逻辑
        pass
```

4. **创建监控服务**
```python
# src/services/new_service_monitor.py
class NewServiceMonitor:
    async def start_monitoring(self):
        # 实现监控逻辑
        pass
```

### 自定义通知模板

```python
# src/services/notification_service.py
def create_custom_template(self, event_type: str, data: Dict):
    templates = {
        "custom_event": {
            "msgtype": "markdown",
            "markdown": {
                "content": f"## 自定义事件通知\n内容: {data}"
            }
        }
    }
    return templates.get(event_type)
```

## 📈 性能优化

- **异步处理**: 所有IO操作使用async/await
- **连接池**: 数据库和HTTP连接复用
- **批量操作**: 数据库批量插入和更新
- **缓存机制**: API响应和价格数据缓存
- **错误重试**: 指数退避重试策略

## 🚨 故障排除

### 常见问题

1. **推特API限制**
```bash
# 检查API限制状态
uv run python check_rate_limit.py
```

2. **Solana RPC连接问题**
```bash
# 测试RPC连接
uv run python tests/test_solana_rpc.py
```

3. **数据库连接问题**
```bash
# 检查数据库连接
uv run python -c "from src.config.database import engine; print(engine.execute('SELECT 1'))"
```

## 📝 更新日志

### v2.0.0 (当前)
- ✅ 插件化监控系统架构
- ✅ 推特监控功能完整实现
- ✅ Solana监控功能完整实现
- ✅ 智能通知推送系统
- ✅ 规则引擎和模板管理
- ✅ 限流去重机制
- ✅ 完整的单元测试覆盖
- ✅ 真实API集成测试
- 🔄 Web管理界面 (计划中)

## 🤝 贡献指南

1. Fork 项目
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add AmazingFeature'`)
4. 推送分支 (`git push origin feature/AmazingFeature`)
5. 创建 Pull Request

## 📄 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情。

## 🙏 致谢

- [FastAPI](https://fastapi.tiangolo.com/) - 现代、快速的Web框架
- [SQLAlchemy](https://www.sqlalchemy.org/) - Python SQL工具包
- [Solana](https://solana.com/) - 高性能区块链平台
- [Twitter API](https://developer.twitter.com/) - 推特开发者平台

## 📞 支持

如有问题或建议，请通过以下方式联系：

- 创建 GitHub Issue
- 发送邮件到: [support@example.com](mailto:support@example.com)
- 项目文档: [docs/](docs/)

---

**⚠️ 免责声明**: 本软件仅供学习和研究使用。在生产环境中使用前，请确保遵守相关API的使用条款和当地法律法规。