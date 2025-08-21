# DEX_SWAP 交易通知增强计划

## 需求分析

当交易类型为 `TransactionType.DEX_SWAP` 时，需要在通知模板中添加以下信息：

1. **Swap代币信息**：交换的代币详情
2. **CA地址**：代币的合约地址
3. **购买次数**：这是第几次购买该代币
4. **购买总金额**：购买该代币的累计总金额

## 实现计划

### 1. 数据库查询逻辑设计

#### 1.1 统计代币购买信息
```sql
-- 统计某钱包购买特定代币的次数和总金额
SELECT 
    COUNT(*) as purchase_count,
    SUM(amount) as total_amount,
    SUM(amount_usd) as total_amount_usd
FROM solana_transactions 
WHERE wallet_id = ? 
  AND transaction_type = 'dex_swap'
  AND token_address = ?
  AND created_at <= ?
```

#### 1.2 需要的新方法
- `SolanaMonitorService.get_token_purchase_stats(wallet_id, token_address, before_time)`

### 2. 通知模板修改

#### 2.1 更新 notification_config.py
在 `solana_transaction` 模板中添加新字段：

```python
content_template="""💰 **检测到Solana交易**

👛 **钱包信息**
- 地址: `{wallet_address}`
- 别名: {wallet_alias}

📊 **交易详情** 
- 类型: {transaction_type}
- 金额: {amount} {token_symbol}
- 代币: {token_name} ({token_symbol})

{dex_swap_info}

⏰ **时间**: {block_time}"""
```

#### 2.2 DEX_SWAP 专用信息模板
```python
dex_swap_info_template = """
🔄 **DEX交换详情**
- 从: {from_amount} {from_token_symbol}
- 到: {to_amount} {to_token_symbol}
- CA地址: `{token_ca_address}`
- 购买次数: 第 {purchase_count} 次
- 累计投入: {total_purchase_amount} SOL (${total_purchase_usd})
"""
```

### 3. 代码实现任务

#### 3.1 SolanaMonitorService 增强 (src/services/solana_monitor.py)
```python
def get_token_purchase_stats(self, wallet_id: int, token_address: str, before_time: datetime) -> dict:
    """
    获取代币购买统计信息
    
    Args:
        wallet_id: 钱包ID
        token_address: 代币合约地址
        before_time: 统计截止时间
        
    Returns:
        {
            'purchase_count': int,      # 购买次数
            'total_sol_amount': float,  # 累计SOL金额
            'total_usd_amount': float   # 累计USD金额
        }
    """
```

#### 3.2 通知数据增强 (src/plugins/solana_monitor_plugin.py)
修改 `_trigger_single_notification` 方法，为 DEX_SWAP 交易添加额外信息：

```python
# 如果是DEX交换，获取代币购买统计
if analysis.transaction_type == TransactionType.DEX_SWAP and analysis.swap_info:
    # 获取代币CA地址
    token_ca = analysis.swap_info.to_token.mint
    
    # 获取购买统计
    purchase_stats = self.solana_monitor.get_token_purchase_stats(
        wallet.id, 
        token_ca, 
        datetime.fromtimestamp(analysis.transaction.block_time)
    )
    
    # 添加DEX交换特殊信息
    notification_data.update({
        "from_amount": analysis.swap_info.from_amount,
        "from_token_symbol": analysis.swap_info.from_token.symbol,
        "to_amount": analysis.swap_info.to_amount,
        "to_token_symbol": analysis.swap_info.to_token.symbol,
        "token_ca_address": token_ca,
        "purchase_count": purchase_stats['purchase_count'],
        "total_purchase_amount": purchase_stats['total_sol_amount'],
        "total_purchase_usd": purchase_stats['total_usd_amount'],
        "dex_swap_info": format_dex_swap_info(purchase_stats, analysis.swap_info)
    })
```

### 4. 实施步骤

#### 阶段1：数据库查询功能
1. ✅ 分析需求和数据结构
2. ✅ 实现 `get_token_purchase_stats` 方法
3. ✅ 编写单元测试验证查询逻辑

#### 阶段2：模板增强
4. ✅ 修改通知配置模板
5. ✅ 添加DEX交换信息格式化函数
6. ✅ 测试模板渲染

#### 阶段3：通知逻辑集成
7. ✅ 修改 `_trigger_single_notification` 方法
8. ✅ 集成代币统计查询
9. ✅ 处理边界情况和异常

#### 阶段4：测试和验证
10. ✅ 创建测试用例
11. ✅ 验证真实DEX交易通知
12. ✅ 性能优化和错误处理

### 5. 技术考虑

#### 5.1 性能优化
- 数据库查询添加索引：`(wallet_id, transaction_type, token_address, created_at)`
- 考虑缓存机制避免重复查询

#### 5.2 数据一致性
- 确保统计时间点正确（使用交易的block_time）
- 处理时区和时间格式

#### 5.3 错误处理
- 查询失败时的降级策略
- 缺少数据时的默认值处理

### 6. 预期效果

#### 6.1 通知示例
```
💰 **检测到Solana交易**

👛 **钱包信息**
- 地址: `AbcD...XyZ`
- 别名: 主钱包

📊 **交易详情** 
- 类型: dex_swap
- 金额: 1250000 BONK
- 代币: Bonk (BONK)

🔄 **DEX交换详情**
- 从: 0.5 SOL
- 到: 1250000 BONK
- CA地址: `DezXAZ8z7PnrnRJjz3wXBoRgixCa6xjnB7YaB1pPB263`
- 购买次数: 第 3 次
- 累计投入: 1.8 SOL ($270.50)

⏰ **时间**: 2025-08-21 16:30:00
```

#### 6.2 用户价值
- 清晰了解代币投资历史
- 快速识别重复购买行为
- 投资决策参考信息

## ✅ 实施完成总结

### 实现完成情况
- **2025-08-21**: 所有4个阶段全部完成
- **代码变更**: 3个主要文件被修改
- **测试验证**: 创建了完整的测试用例并验证功能

### 核心实现文件
1. **src/services/solana_monitor.py**: 
   - 添加了 `get_token_purchase_stats` 方法
   - 支持查询钱包对特定代币的购买统计

2. **src/config/notification_config.py**:
   - 修改了 `solana_transaction` 模板
   - 添加了 `{dex_swap_info}` 占位符

3. **src/plugins/solana_monitor_plugin.py**:
   - 增强了 `_trigger_single_notification` 方法
   - 集成了DEX交换信息统计和格式化

### 功能特性
- ✅ 代币购买次数统计
- ✅ 累计投入金额计算（SOL和USD）
- ✅ 代币合约地址（CA地址）显示
- ✅ 交换详情格式化（从什么到什么）
- ✅ 错误处理和降级策略

### 测试文件
- **test_dex_swap_enhancement.py**: 完整的功能验证测试

## 下一步行动

功能已完成并可投入使用。建议在生产环境中监控通知效果，必要时可进一步优化统计查询性能。