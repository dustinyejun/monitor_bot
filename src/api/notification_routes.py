"""
通知系统API路由
"""
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy.orm import Session

from ..config.database import get_db
from ..services.notification_service import notification_service
# 移除模板和规则管理服务依赖，改用硬编码配置
from ..schemas.notification import (
    NotificationCreate, NotificationResponse, NotificationSearchRequest, NotificationStatsResponse,
    NotificationTriggerRequest
)
from ..models.notification import Notification

router = APIRouter(prefix="/api/notification", tags=["notifications"])


@router.post("/send", response_model=dict)
async def send_notification(notification_data: NotificationCreate):
    """发送通知"""
    try:
        success = await notification_service.send_notification(notification_data)
        return {"success": success, "message": "通知发送成功" if success else "通知发送失败"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/send-by-template", response_model=dict)
async def send_notification_by_template(trigger_request: NotificationTriggerRequest):
    """使用模板发送通知"""
    try:
        success = await notification_service.send_by_template(trigger_request)
        return {"success": success, "message": "通知发送成功" if success else "通知发送失败"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/list", response_model=List[NotificationResponse])
async def list_notifications(
    type: Optional[str] = Query(None, description="通知类型过滤"),
    status: Optional[str] = Query(None, description="状态过滤"),
    limit: int = Query(20, ge=1, le=100, description="返回数量"),
    offset: int = Query(0, ge=0, description="偏移量"),
    db: Session = Depends(get_db)
):
    """获取通知列表"""
    try:
        query = db.query(Notification)
        
        if type:
            query = query.filter(Notification.type == type)
        if status:
            query = query.filter(Notification.status == status)
        
        notifications = query.order_by(
            Notification.created_at.desc()
        ).offset(offset).limit(limit).all()
        
        return [NotificationResponse.from_orm(n) for n in notifications]
    
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/stats", response_model=NotificationStatsResponse)
async def get_notification_stats():
    """获取通知统计信息"""
    try:
        stats = await notification_service.get_notification_stats()
        return NotificationStatsResponse(**stats)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/retry-failed", response_model=dict)
async def retry_failed_notifications():
    """重试失败的通知"""
    try:
        retry_count = await notification_service.retry_failed_notifications()
        return {"retry_count": retry_count, "message": f"重试了 {retry_count} 条失败通知"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# 模板和规则管理接口已移除 - 现在使用硬编码配置
# 如需查看或修改配置，请编辑 src/config/notification_config.py

# 配置信息接口
@router.get("/config", response_model=dict)
async def get_notification_config():
    """获取当前通知配置信息"""
    try:
        from ..config.notification_config import get_all_templates, get_all_rules
        
        templates = {name: {
            "name": template.name,
            "type": template.type,
            "title_template": template.title_template,
            "channel": template.channel,
            "is_urgent": template.is_urgent
        } for name, template in get_all_templates().items()}
        
        rules = {name: {
            "name": rule.name,
            "type": rule.type,
            "template_name": rule.template_name,
            "is_active": rule.is_active,
            "priority": rule.priority,
            "rate_limit_enabled": rule.rate_limit_enabled,
            "rate_limit_count": rule.rate_limit_count,
            "rate_limit_window_seconds": rule.rate_limit_window_seconds
        } for name, rule in get_all_rules().items()}
        
        return {
            "templates": templates,
            "rules": rules,
            "config_location": "src/config/notification_config.py"
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# 测试接口
@router.post("/test", response_model=dict)
async def test_notification():
    """测试通知发送"""
    try:
        test_notification = NotificationCreate(
            type="system",
            title="🧪 通知系统测试",
            content="这是一条测试通知，用于验证通知系统是否正常工作。",
            is_urgent=False,
            channel="wechat",
            data={"test": True}
        )
        
        success = await notification_service.send_notification(test_notification)
        return {
            "success": success,
            "message": "测试通知发送成功" if success else "测试通知发送失败"
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/test-template", response_model=dict)
async def test_notification_template():
    """测试模板通知"""
    try:
        test_trigger = NotificationTriggerRequest(
            template_name="solana_transaction",
            variables={
                "wallet_alias": "测试钱包",
                "wallet_address": "1234567890abcdef1234567890abcdef12345678",
                "transaction_type": "sol_transfer",
                "amount": "10.5",
                "token_symbol": "SOL",
                "amount_usd": "150.25",
                "token_name": "Solana",
                "solscan_url": "https://solscan.io/tx/test",
                "signature": "test_signature_123456789",
                "block_time": "2025-08-21 10:30:00"
            }
        )
        
        success = await notification_service.send_by_template(test_trigger)
        return {
            "success": success,
            "message": "模板测试通知发送成功" if success else "模板测试通知发送失败"
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))