"""
硬编码的通知模板和规则配置
简化设计，移除数据库依赖
"""
from dataclasses import dataclass
from typing import Dict, Any, List


@dataclass
class NotificationTemplate:
    """通知模板配置"""
    name: str
    type: str
    title_template: str
    content_template: str
    is_urgent: bool = False
    channel: str = "wechat"
    dedup_enabled: bool = True
    dedup_window_seconds: int = 300


@dataclass
class NotificationRule:
    """通知规则配置"""
    name: str
    type: str
    conditions: Dict[str, Any]
    template_name: str
    is_active: bool = True
    priority: int = 0
    rate_limit_enabled: bool = True
    rate_limit_count: int = 10
    rate_limit_window_seconds: int = 3600


# =============================================================================
# 通知模板配置
# =============================================================================

NOTIFICATION_TEMPLATES = {
    # Solana交易监控模板
    "solana_transaction": NotificationTemplate(
        name="solana_transaction",
        type="solana",
        title_template="🔔 Solana交易监控 - {wallet_alias}",
        content_template="""💰 **检测到Solana交易**

👛 **钱包信息**
- 地址: `{wallet_address}`
- 别名: {wallet_alias}

📊 **交易详情** 
- 类型: {transaction_type}
- 金额: {amount} {token_symbol}
- 代币: {token_name} ({token_symbol})

{dex_swap_info}

⏰ **时间**: {block_time}""",
        is_urgent=False,
        channel="wechat",
        dedup_enabled=True,
        dedup_window_seconds=60  # 1分钟去重
    ),
    
    # Twitter CA地址监控模板
    "twitter_ca_alert": NotificationTemplate(
        name="twitter_ca_alert",
        type="twitter",
        title_template="🚨 CA地址推文提醒",
        content_template="""### 📱 用户: {username}
**推文内容**: {content}

**CA地址**: `{ca_addresses}`

**推文链接**: {tweet_url}

**发布时间**: {tweet_created_at}""",
        is_urgent=True,
        channel="wechat",
        dedup_enabled=True,
        dedup_window_seconds=300  # 5分钟去重
    )
}


# =============================================================================
# 通知规则配置
# =============================================================================

NOTIFICATION_RULES = {
    # Solana交易监控规则
    "solana_transaction_rule": NotificationRule(
        name="solana_transaction_rule",
        type="solana",
        conditions={
            "or": [
                # 1. SOL转账 (≥钱包设置的阈值)
                {
                    "and": [
                        {
                            "field": "transaction_type",
                            "operator": "eq",
                            "value": "sol_transfer"
                        },
                        {
                            "field": "amount_usd",
                            "operator": "gte",
                            "value": 0.01  # 当前钱包最低阈值
                        }
                    ]
                },
                # 2. 所有DEX交换
                {
                    "field": "transaction_type",
                    "operator": "eq",
                    "value": "dex_swap"
                },
                # 3. 金额超过1美元的任何交易
                {
                    "field": "amount_usd",
                    "operator": "gte",
                    "value": 1.0
                }
            ]
        },
        template_name="solana_transaction",
        is_active=True,
        priority=5,
        rate_limit_enabled=True,
        rate_limit_count=20,  # 相对宽松的限制
        rate_limit_window_seconds=300  # 5分钟内最多20条
    ),
    
    # Twitter CA地址检测规则
    "twitter_ca_detection": NotificationRule(
        name="twitter_ca_detection",
        type="twitter",
        conditions={
            "and": [
                {
                    "field": "ca_addresses",
                    "operator": "ne",
                    "value": []
                },
                {
                    "field": "content",
                    "operator": "contains",
                    "value": "CA"
                }
            ]
        },
        template_name="twitter_ca_alert",
        is_active=True,
        priority=10,
        rate_limit_enabled=True,
        rate_limit_count=5,
        rate_limit_window_seconds=300  # 5分钟内最多5条
    )
}


# =============================================================================
# 辅助函数
# =============================================================================

def get_template(template_name: str) -> NotificationTemplate:
    """获取通知模板"""
    template = NOTIFICATION_TEMPLATES.get(template_name)
    if not template:
        raise ValueError(f"通知模板不存在: {template_name}")
    return template


def get_rules_by_type(rule_type: str, active_only: bool = True) -> List[NotificationRule]:
    """根据类型获取规则列表"""
    rules = []
    for rule in NOTIFICATION_RULES.values():
        if rule.type == rule_type:
            if not active_only or rule.is_active:
                rules.append(rule)
    
    # 按优先级排序 (优先级高的先执行)
    return sorted(rules, key=lambda r: r.priority, reverse=True)


def get_all_templates() -> Dict[str, NotificationTemplate]:
    """获取所有模板"""
    return NOTIFICATION_TEMPLATES.copy()


def get_all_rules() -> Dict[str, NotificationRule]:
    """获取所有规则"""
    return NOTIFICATION_RULES.copy()


# =============================================================================
# 配置验证
# =============================================================================

def validate_config():
    """验证配置完整性"""
    errors = []
    
    # 检查规则引用的模板是否存在
    for rule_name, rule in NOTIFICATION_RULES.items():
        if rule.template_name not in NOTIFICATION_TEMPLATES:
            errors.append(f"规则 '{rule_name}' 引用的模板 '{rule.template_name}' 不存在")
    
    # 检查模板变量格式（简化验证，只检查大括号配对）
    for template_name, template in NOTIFICATION_TEMPLATES.items():
        try:
            # 检查标题模板的大括号配对
            title_open = template.title_template.count('{')
            title_close = template.title_template.count('}')
            if title_open != title_close:
                errors.append(f"模板 '{template_name}' 标题模板大括号配对错误")
            
            # 检查内容模板的大括号配对
            content_open = template.content_template.count('{')
            content_close = template.content_template.count('}')
            if content_open != content_close:
                errors.append(f"模板 '{template_name}' 内容模板大括号配对错误")
                
        except Exception as e:
            errors.append(f"模板 '{template_name}' 验证异常: {e}")
    
    if errors:
        raise ValueError("配置验证失败:\n" + "\n".join(errors))
    
    return True


# 启动时验证配置
validate_config()