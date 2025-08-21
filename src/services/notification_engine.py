"""
通知触发引擎
根据规则自动触发通知
"""
import json
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Callable
from sqlalchemy.orm import Session
from sqlalchemy import and_, func
from loguru import logger

from ..config.database import SessionLocal
from ..models.notification import Notification
from ..schemas.notification import NotificationTriggerRequest
from .notification_service import notification_service
# 移除template_service依赖，改用硬编码配置


class NotificationEngine:
    """通知触发引擎"""
    
    def __init__(self):
        self.rate_limit_cache = {}  # 简单的内存限流缓存
        self.condition_handlers = self._init_condition_handlers()
    
    def _init_condition_handlers(self) -> Dict[str, Callable]:
        """初始化条件处理器"""
        return {
            # 数值比较
            "gt": lambda value, threshold: float(value) > float(threshold),
            "gte": lambda value, threshold: float(value) >= float(threshold),
            "lt": lambda value, threshold: float(value) < float(threshold),
            "lte": lambda value, threshold: float(value) <= float(threshold),
            "eq": lambda value, threshold: value == threshold,
            "ne": lambda value, threshold: value != threshold,
            
            # 字符串匹配
            "contains": lambda value, pattern: pattern.lower() in str(value).lower(),
            "startswith": lambda value, pattern: str(value).lower().startswith(pattern.lower()),
            "endswith": lambda value, pattern: str(value).lower().endswith(pattern.lower()),
            "in": lambda value, options: value in options,
            "not_in": lambda value, options: value not in options,
            
            # 正则表达式
            "regex": lambda value, pattern: self._regex_match(str(value), pattern),
            
            # 时间比较
            "within_minutes": lambda timestamp, minutes: self._within_minutes(timestamp, minutes),
            "within_hours": lambda timestamp, hours: self._within_hours(timestamp, hours),
        }
    
    def _regex_match(self, value: str, pattern: str) -> bool:
        """正则表达式匹配"""
        import re
        try:
            return bool(re.search(pattern, value, re.IGNORECASE))
        except Exception as e:
            logger.error(f"正则表达式匹配失败: {e}")
            return False
    
    def _within_minutes(self, timestamp: Any, minutes: int) -> bool:
        """检查时间是否在指定分钟内"""
        try:
            if isinstance(timestamp, str):
                ts = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            elif isinstance(timestamp, datetime):
                ts = timestamp
            else:
                return False
            
            now = datetime.utcnow()
            return (now - ts).total_seconds() <= minutes * 60
        except Exception:
            return False
    
    def _within_hours(self, timestamp: Any, hours: int) -> bool:
        """检查时间是否在指定小时内"""
        return self._within_minutes(timestamp, hours * 60)
    
    async def check_twitter_rules(self, tweet_data: Dict[str, Any]) -> bool:
        """检查Twitter相关规则"""
        try:
            # 从硬编码配置获取规则
            from ..config.notification_config import get_rules_by_type
            
            rules = get_rules_by_type("twitter", active_only=True)
            
            for rule in rules:
                try:
                    if self._evaluate_conditions(tweet_data, rule.conditions):
                        # 检查限流
                        if await self._check_rate_limit(rule.name, rule.rate_limit_enabled, 
                                                     rule.rate_limit_count, rule.rate_limit_window_seconds):
                            # 触发通知
                            await self._trigger_notification(rule.template_name, tweet_data)
                            logger.info(f"Twitter规则触发通知: {rule.name}")
                        else:
                            logger.warning(f"Twitter规则触发被限流: {rule.name}")
                
                except Exception as e:
                    logger.error(f"处理Twitter规则失败 {rule.name}: {e}")
            
            return True
        
        except Exception as e:
            logger.error(f"检查Twitter规则失败: {e}")
            return False
    
    async def check_solana_rules(self, transaction_data: Dict[str, Any]) -> bool:
        """检查Solana相关规则"""
        try:
            # 从硬编码配置获取规则
            from ..config.notification_config import get_rules_by_type
            
            rules = get_rules_by_type("solana", active_only=True)
            
            for rule in rules:
                try:
                    if self._evaluate_conditions(transaction_data, rule.conditions):
                        # 检查限流
                        if await self._check_rate_limit(rule.name, rule.rate_limit_enabled,
                                                     rule.rate_limit_count, rule.rate_limit_window_seconds):
                            # 触发通知
                            await self._trigger_notification(rule.template_name, transaction_data)
                            logger.info(f"Solana规则触发通知: {rule.name}")
                        else:
                            logger.warning(f"Solana规则触发被限流: {rule.name}")
                
                except Exception as e:
                    logger.error(f"处理Solana规则失败 {rule.name}: {e}")
            
            return True
        
        except Exception as e:
            logger.error(f"检查Solana规则失败: {e}")
            return False
    
    async def check_system_rules(self, system_data: Dict[str, Any]) -> bool:
        """检查系统相关规则"""
        try:
            # 从硬编码配置获取规则
            from ..config.notification_config import get_rules_by_type
            
            rules = get_rules_by_type("system", active_only=True)
            
            for rule in rules:
                try:
                    if self._evaluate_conditions(system_data, rule.conditions):
                        # 检查限流
                        if await self._check_rate_limit(rule.name, rule.rate_limit_enabled,
                                                     rule.rate_limit_count, rule.rate_limit_window_seconds):
                            # 触发通知
                            await self._trigger_notification(rule.template_name, system_data)
                            logger.info(f"系统规则触发通知: {rule.name}")
                        else:
                            logger.warning(f"系统规则触发被限流: {rule.name}")
                
                except Exception as e:
                    logger.error(f"处理系统规则失败 {rule.name}: {e}")
            
            return True
        
        except Exception as e:
            logger.error(f"检查系统规则失败: {e}")
            return False
    
    def _evaluate_conditions(self, data: Dict[str, Any], conditions: Dict[str, Any]) -> bool:
        """评估触发条件"""
        try:
            # 支持AND和OR逻辑
            if "and" in conditions:
                return all(self._evaluate_condition_group(data, cond) for cond in conditions["and"])
            elif "or" in conditions:
                return any(self._evaluate_condition_group(data, cond) for cond in conditions["or"])
            else:
                return self._evaluate_condition_group(data, conditions)
        
        except Exception as e:
            logger.error(f"评估条件失败: {e}")
            return False
    
    def _evaluate_condition_group(self, data: Dict[str, Any], condition: Dict[str, Any]) -> bool:
        """评估单个条件组"""
        try:
            field = condition.get("field")
            operator = condition.get("operator")
            value = condition.get("value")
            
            if not all([field, operator]):
                return False
            
            # 获取数据字段值，支持嵌套字段
            data_value = self._get_nested_value(data, field)
            if data_value is None:
                return False
            
            # 执行条件判断
            handler = self.condition_handlers.get(operator)
            if not handler:
                logger.error(f"不支持的操作符: {operator}")
                return False
            
            return handler(data_value, value)
        
        except Exception as e:
            logger.error(f"评估条件组失败: {e}")
            return False
    
    def _get_nested_value(self, data: Dict[str, Any], field: str) -> Any:
        """获取嵌套字段值"""
        try:
            keys = field.split('.')
            value = data
            
            for key in keys:
                if isinstance(value, dict) and key in value:
                    value = value[key]
                else:
                    return None
            
            return value
        
        except Exception:
            return None
    
    async def _check_rate_limit(self, rule_name: str, enabled: bool, 
                              count: int, window_seconds: int) -> bool:
        """检查限流"""
        if not enabled:
            return True
        
        try:
            # 使用数据库进行限流检查（更准确）
            db = SessionLocal()
            try:
                cutoff_time = datetime.utcnow() - timedelta(seconds=window_seconds)
                
                # 计算时间窗口内的通知数量
                recent_count = db.query(Notification).filter(
                    and_(
                        Notification.data.op('->>')('rule_name') == rule_name,
                        Notification.created_at > cutoff_time,
                        Notification.status.in_(["sent", "pending"])
                    )
                ).count()
                
                return recent_count < count
            
            finally:
                db.close()
        
        except Exception as e:
            logger.error(f"检查限流失败: {e}")
            return True  # 失败时允许通过
    
    async def _trigger_notification(self, template_name: str, variables: Dict[str, Any]) -> bool:
        """触发通知"""
        try:
            # 添加规则信息到变量中
            variables["rule_name"] = template_name
            variables["triggered_at"] = datetime.utcnow().isoformat()
            
            trigger_request = NotificationTriggerRequest(
                template_name=template_name,
                variables=variables
            )
            
            return await notification_service.send_by_template(trigger_request)
        
        except Exception as e:
            logger.error(f"触发通知失败: {e}")
            return False


# 注释：默认规则现在在 src/config/notification_config.py 中硬编码定义


# 全局通知引擎实例
notification_engine = NotificationEngine()