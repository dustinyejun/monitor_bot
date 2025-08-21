"""
通知系统数据模型
"""
from datetime import datetime
from typing import Optional, Dict, Any
from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, JSON
from sqlalchemy.orm import relationship
from .base import BaseModel


class Notification(BaseModel):
    """通知记录表"""
    __tablename__ = "notifications"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # 通知基本信息
    type = Column(String(50), nullable=False, comment="通知类型: twitter, solana, system")
    title = Column(String(200), nullable=False, comment="通知标题")
    content = Column(Text, nullable=False, comment="通知内容")
    
    # 通知状态
    status = Column(String(20), default="pending", comment="通知状态: pending, sent, failed")
    is_urgent = Column(Boolean, default=False, comment="是否紧急通知")
    
    # 通知渠道
    channel = Column(String(50), default="wechat", comment="通知渠道: wechat, email, sms")
    
    # 关联数据
    related_type = Column(String(50), nullable=True, comment="关联数据类型")
    related_id = Column(String(100), nullable=True, comment="关联数据ID")
    
    # 扩展数据
    data = Column(JSON, nullable=True, comment="扩展数据")
    
    # 发送信息
    sent_at = Column(DateTime, nullable=True, comment="发送时间")
    error_message = Column(Text, nullable=True, comment="错误信息")
    retry_count = Column(Integer, default=0, comment="重试次数")
    
    # 通知去重
    dedup_key = Column(String(255), nullable=True, index=True, comment="去重键")
    
    # 时间戳
    created_at = Column(DateTime, default=datetime.utcnow, comment="创建时间")
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, comment="更新时间")

    def __repr__(self):
        return f"<Notification(id={self.id}, type={self.type}, title={self.title}, status={self.status})>"


# NotificationTemplate 和 NotificationRule 模型已移除
# 模板和规则配置现在在 src/config/notification_config.py 中硬编码定义