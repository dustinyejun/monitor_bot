from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from datetime import datetime


class BaseResponse(BaseModel):
    """基础响应模式"""
    success: bool = Field(True, description="请求是否成功")
    message: str = Field("操作成功", description="响应消息")
    data: Optional[Any] = Field(None, description="响应数据")
    timestamp: datetime = Field(default_factory=datetime.now, description="响应时间戳")


class ErrorResponse(BaseModel):
    """错误响应模式"""
    success: bool = Field(False, description="请求是否成功")
    message: str = Field(..., description="错误消息")
    error_code: Optional[str] = Field(None, description="错误代码")
    details: Optional[Dict[str, Any]] = Field(None, description="错误详情")
    timestamp: datetime = Field(default_factory=datetime.now, description="响应时间戳")


class PaginationResponse(BaseModel):
    """分页响应模式"""
    items: List[Any] = Field(default_factory=list, description="数据项")
    total: int = Field(..., description="总数量")
    page: int = Field(..., description="当前页码")
    size: int = Field(..., description="每页大小")
    pages: int = Field(..., description="总页数")
    has_next: bool = Field(..., description="是否有下一页")
    has_prev: bool = Field(..., description="是否有上一页")


class SystemStatusResponse(BaseModel):
    """系统状态响应模式"""
    status: str = Field(..., description="系统状态")
    uptime: float = Field(..., description="运行时间（秒）")
    version: str = Field(..., description="系统版本")
    
    # 数据库状态
    database_connected: bool = Field(..., description="数据库连接状态")
    
    # 任务状态
    scheduler_running: bool = Field(..., description="调度器运行状态")
    twitter_monitor_active: bool = Field(..., description="推特监控状态")
    solana_monitor_active: bool = Field(..., description="Solana监控状态")
    
    # 统计信息
    total_users: int = Field(0, description="总用户数")
    total_wallets: int = Field(0, description="总钱包数")
    total_tweets: int = Field(0, description="总推文数")
    total_transactions: int = Field(0, description="总交易数")
    
    # 最后活动时间
    last_twitter_check: Optional[datetime] = Field(None, description="最后推特检查时间")
    last_solana_check: Optional[datetime] = Field(None, description="最后Solana检查时间")


class TaskStatusResponse(BaseModel):
    """任务状态响应模式"""
    task_id: str = Field(..., description="任务ID")
    task_name: str = Field(..., description="任务名称")
    status: str = Field(..., description="任务状态")
    next_run_time: Optional[datetime] = Field(None, description="下次运行时间")
    last_run_time: Optional[datetime] = Field(None, description="上次运行时间")
    run_count: int = Field(0, description="运行次数")
    success_count: int = Field(0, description="成功次数")
    error_count: int = Field(0, description="错误次数")


class ConfigResponse(BaseModel):
    """配置响应模式"""
    twitter_check_interval: int = Field(..., description="推特检查间隔")
    solana_check_interval: int = Field(..., description="Solana检查间隔")
    debug_mode: bool = Field(..., description="调试模式")
    log_level: str = Field(..., description="日志级别")


class HealthCheckResponse(BaseModel):
    """健康检查响应模式"""
    healthy: bool = Field(..., description="系统是否健康")
    checks: Dict[str, bool] = Field(default_factory=dict, description="各项检查结果")
    details: Optional[Dict[str, Any]] = Field(None, description="详细信息")