# 推特API测试指南

## 🎯 测试目标
验证推特监控系统能否成功连接和使用真实的推特API v2。

## 📋 准备工作

### 1. 获取推特API访问权限

#### 步骤1: 创建推特开发者账户
1. 访问 [Twitter Developer Platform](https://developer.twitter.com/)
2. 使用您的推特账户登录
3. 点击 "Apply for a developer account"
4. 填写申请表单:
   - 选择用途: "Making a bot" 或 "Academic research"
   - 描述您的使用场景: "监控加密货币相关推文"
   - 同意开发者协议

#### 步骤2: 创建应用程序
1. 登录 [Twitter Developer Portal](https://developer.twitter.com/en/portal/dashboard)
2. 点击 "Create an App"
3. 填写应用信息:
   - App name: "Monitor Bot"
   - Description: "Twitter monitoring bot for cryptocurrency content"
   - Website URL: 可以填写 GitHub 仓库地址
   - Use case: 选择适合的用例

#### 步骤3: 获取API密钥
1. 在应用详情页面，点击 "Keys and tokens"
2. 找到 "Bearer Token" 部分
3. 点击 "Generate" 生成Bearer Token
4. **重要**: 立即复制并保存这个Token，它只显示一次

### 2. 配置环境变量

创建或更新 `.env` 文件:

```bash
# 复制环境变量模板
cp .env.example .env

# 编辑 .env 文件
vim .env  # 或使用您喜欢的编辑器
```

在 `.env` 文件中添加:
```
TWITTER_BEARER_TOKEN=你的Bearer Token
```

### 3. 验证配置

```bash
# 检查环境变量是否设置成功
echo $TWITTER_BEARER_TOKEN
```

## 🚀 执行测试

### 方法1: 运行完整测试套件

```bash
# 运行所有测试
uv run python tests/test_real_twitter_api.py
```

### 方法2: 交互式测试

创建一个简单的交互式测试脚本:

```bash
# 创建快速测试脚本
cat > quick_test.py << 'EOF'
import asyncio
import os
from src.services.twitter_client import TwitterClient

async def quick_test():
    token = os.getenv('TWITTER_BEARER_TOKEN')
    if not token:
        print("❌ 请设置 TWITTER_BEARER_TOKEN 环境变量")
        return
        
    async with TwitterClient(token) as client:
        # 测试获取用户信息
        user = await client.get_user_by_username("elonmusk")
        if user:
            print(f"✅ 成功获取用户: {user.name} (@{user.username})")
            print(f"   粉丝数: {user.public_metrics.get('followers_count', 'N/A')}")
        else:
            print("❌ 获取用户信息失败")

if __name__ == "__main__":
    asyncio.run(quick_test())
EOF

# 运行快速测试
uv run python quick_test.py
```

## 📊 测试内容说明

### 测试1: API连接验证
- 验证Bearer Token有效性
- 检查API响应状态
- 显示当前速率限制信息

### 测试2: 用户信息获取
- 获取指定用户的基本信息
- 验证用户ID、用户名、显示名等
- 测试用户不存在的情况处理

### 测试3: 推文获取
- 获取用户最近的推文
- 验证推文内容、时间戳、互动数据
- 测试分页和数量限制

### 测试4: CA地址分析
- 对获取的推文进行CA地址识别
- 测试多链地址支持 (ETH/BSC/SOL等)
- 验证置信度计算和风险评分

### 测试5: 速率限制处理
- 测试连续请求的速率限制
- 验证重试机制
- 检查限制重置时间

## 🔧 故障排除

### 常见问题及解决方案

#### 1. Bearer Token无效
```
❌ API连接失败: Unauthorized
```
**解决方案**: 
- 检查Token是否正确复制
- 确认Token未过期
- 重新生成Bearer Token

#### 2. 速率限制
```
❌ API请求失败: 429 - Too Many Requests
```
**解决方案**:
- 等待速率限制重置 (通常15分钟)
- 减少测试请求频率
- 检查其他应用是否在使用相同Token

#### 3. 网络连接问题
```
❌ 网络请求失败: Connection timeout
```
**解决方案**:
- 检查网络连接
- 确认防火墙设置
- 尝试使用代理

#### 4. 用户不存在
```
❌ 用户 @username 不存在
```
**解决方案**:
- 确认用户名拼写正确
- 尝试其他公开用户账户
- 检查用户是否被暂停或删除

## 📈 测试结果解读

### 成功指标
- ✅ 所有API调用返回200状态码
- ✅ 成功获取用户信息和推文数据
- ✅ CA地址识别功能正常
- ✅ 速率限制正确处理

### 性能基准
- API响应时间: < 2秒
- 用户信息获取: < 1秒
- 推文获取(10条): < 3秒
- CA地址分析: < 0.5秒/推文

## 🔄 自动化测试

您也可以设置定时测试:

```bash
# 创建定时测试脚本
cat > schedule_test.sh << 'EOF'
#!/bin/bash
echo "$(date): 开始推特API测试" >> api_test.log
cd /Users/yejun/workspace/monitor_bot
uv run python tests/test_real_twitter_api.py >> api_test.log 2>&1
echo "$(date): 测试完成" >> api_test.log
echo "---" >> api_test.log
EOF

chmod +x schedule_test.sh

# 使用cron定时运行 (每小时测试一次)
# crontab -e
# 0 * * * * /path/to/schedule_test.sh
```

## 📝 测试报告

测试完成后，您会看到类似以下的输出:

```
🚀 开始推特API完整测试...

==================================================
🔧 测试1: API连接...
✅ API连接成功
   剩余请求数: 75
   重置时间: 2024-01-19 17:30:00

🔧 测试2: 获取用户信息 (@elonmusk)...
✅ 用户信息获取成功:
   用户ID: 44196397
   用户名: @elonmusk
   显示名: Elon Musk
   粉丝数: 150000000
   关注数: 500

🔧 测试3: 获取用户推文 (@elonmusk, 最近5条)...
✅ 成功获取 5 条推文:
   推文 1:
   ID: 1748xxxx
   时间: 2024-01-19T16:00:00.000Z
   内容: 推文内容...
   
📊 分析结果: 5 条推文中发现 0 条包含CA地址

==================================================
🎉 推特API测试完成!
```

现在您可以运行测试来验证推特API集成是否成功！