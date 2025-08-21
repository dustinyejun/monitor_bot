"""
通知系统相关的Pydantic模式
"""
from datetime import datetime
from typing import List, Optional, Dict, Any, Union
from pydantic import BaseModel, Field, validator
from enum import Enum


class NotificationStatus(str, Enum):
    """通知状态"""
    PENDING = "pending"
    SENT = "sent" 
    FAILED = "failed"


class NotificationChannel(str, Enum):
    """通知渠道"""
    WECHAT = "wechat"
    EMAIL = "email"
    SMS = "sms"


class NotificationType(str, Enum):
    """通知类型"""
    TWITTER = "twitter"
    SOLANA = "solana"
    # SYSTEM = "system"  # 已移除：专注于核心监控功能


class NotificationBase(BaseModel):
    """通知基础模式"""
    type: NotificationType = Field(..., description="通知类型")
    title: str = Field(..., max_length=200, description="通知标题")
    content: str = Field(..., description="通知内容")
    is_urgent: bool = Field(False, description="是否紧急通知")
    channel: NotificationChannel = Field(NotificationChannel.WECHAT, description="通知渠道")
    related_type: Optional[str] = Field(None, max_length=50, description="关联数据类型")
    related_id: Optional[str] = Field(None, max_length=100, description="关联数据ID")
    data: Optional[Dict[str, Any]] = Field(default_factory=dict, description="扩展数据")


class NotificationCreate(NotificationBase):
    """创建通知请求"""
    dedup_key: Optional[str] = Field(None, max_length=255, description="去重键")


class NotificationResponse(NotificationBase):
    """通知响应"""
    id: int = Field(..., description="通知ID")
    status: NotificationStatus = Field(..., description="通知状态")
    sent_at: Optional[datetime] = Field(None, description="发送时间")
    error_message: Optional[str] = Field(None, description="错误信息")
    retry_count: int = Field(0, description="重试次数")
    dedup_key: Optional[str] = Field(None, description="去重键")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")
    
    class Config:
        from_attributes = True


class NotificationTemplateBase(BaseModel):
    """通知模板基础模式"""
    name: str = Field(..., max_length=100, description="模板名称")
    type: NotificationType = Field(..., description="通知类型")
    title_template: str = Field(..., max_length=200, description="标题模板")
    content_template: str = Field(..., description="内容模板")
    is_active: bool = Field(True, description="是否启用")
    is_urgent: bool = Field(False, description="是否紧急模板")
    channel: NotificationChannel = Field(NotificationChannel.WECHAT, description="默认通知渠道")
    dedup_enabled: bool = Field(True, description="是否启用去重")
    dedup_window_seconds: int = Field(300, ge=0, description="去重时间窗口(秒)")
    variables: Optional[Dict[str, str]] = Field(default_factory=dict, description="模板变量说明")


class NotificationTemplateCreate(NotificationTemplateBase):
    """创建通知模板"""
    pass


class NotificationTemplateUpdate(BaseModel):
    """更新通知模板"""
    title_template: Optional[str] = Field(None, max_length=200)
    content_template: Optional[str] = None
    is_active: Optional[bool] = None
    is_urgent: Optional[bool] = None
    channel: Optional[NotificationChannel] = None
    dedup_enabled: Optional[bool] = None
    dedup_window_seconds: Optional[int] = Field(None, ge=0)
    variables: Optional[Dict[str, str]] = None


class NotificationTemplateResponse(NotificationTemplateBase):
    """通知模板响应"""
    id: int = Field(..., description="模板ID")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")
    
    class Config:
        from_attributes = True


class NotificationRuleBase(BaseModel):
    """通知规则基础模式"""
    name: str = Field(..., max_length=100, description="规则名称")
    type: NotificationType = Field(..., description="监控类型")
    conditions: Dict[str, Any] = Field(..., description="触发条件")
    template_name: str = Field(..., max_length=100, description="使用的模板名称")
    is_active: bool = Field(True, description="是否启用")
    priority: int = Field(0, description="优先级")
    rate_limit_enabled: bool = Field(True, description="是否启用限流")
    rate_limit_count: int = Field(10, ge=1, description="限流次数")
    rate_limit_window_seconds: int = Field(3600, ge=1, description="限流时间窗口(秒)")


class NotificationRuleCreate(NotificationRuleBase):
    """创建通知规则"""
    pass


class NotificationRuleUpdate(BaseModel):
    """更新通知规则"""
    conditions: Optional[Dict[str, Any]] = None
    template_name: Optional[str] = Field(None, max_length=100)
    is_active: Optional[bool] = None
    priority: Optional[int] = None
    rate_limit_enabled: Optional[bool] = None
    rate_limit_count: Optional[int] = Field(None, ge=1)
    rate_limit_window_seconds: Optional[int] = Field(None, ge=1)


class NotificationRuleResponse(NotificationRuleBase):
    """通知规则响应"""
    id: int = Field(..., description="规则ID")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")
    
    class Config:
        from_attributes = True


class NotificationSearchRequest(BaseModel):
    """通知搜索请求"""
    type: Optional[NotificationType] = Field(None, description="通知类型过滤")
    status: Optional[NotificationStatus] = Field(None, description="状态过滤")
    channel: Optional[NotificationChannel] = Field(None, description="渠道过滤")
    is_urgent: Optional[bool] = Field(None, description="是否紧急过滤")
    start_date: Optional[str] = Field(None, description="开始日期")
    end_date: Optional[str] = Field(None, description="结束日期")
    limit: int = Field(20, ge=1, le=100, description="返回数量")
    offset: int = Field(0, ge=0, description="偏移量")


class NotificationStatsResponse(BaseModel):
    """通知统计响应"""
    total_notifications: int = Field(..., description="总通知数")
    sent_notifications: int = Field(..., description="已发送通知数")
    failed_notifications: int = Field(..., description="发送失败通知数")
    pending_notifications: int = Field(..., description="待发送通知数")
    urgent_notifications: int = Field(..., description="紧急通知数")
    today_notifications: int = Field(..., description="今日通知数")
    
    # 按类型统计
    type_stats: Dict[str, int] = Field(default_factory=dict, description="按类型统计")
    channel_stats: Dict[str, int] = Field(default_factory=dict, description="按渠道统计")
    
    # 成功率
    success_rate: float = Field(..., description="发送成功率")


class WeChatMessage(BaseModel):
    """企业微信消息格式"""
    msgtype: str = Field(..., description="消息类型")
    markdown: Optional[Dict[str, str]] = Field(None, description="markdown消息内容")
    text: Optional[Dict[str, str]] = Field(None, description="文本消息内容")
    
    @validator('msgtype')
    def validate_msgtype(cls, v):
        if v not in ['text', 'markdown']:
            raise ValueError('msgtype必须是text或markdown')
        return v


class NotificationTriggerRequest(BaseModel):
    """通知触发请求"""
    template_name: str = Field(..., description="模板名称")
    variables: Dict[str, Any] = Field(default_factory=dict, description="模板变量")
    override_urgent: Optional[bool] = Field(None, description="覆盖紧急标志")
    override_channel: Optional[NotificationChannel] = Field(None, description="覆盖通知渠道")
    dedup_key: Optional[str] = Field(None, description="自定义去重键")