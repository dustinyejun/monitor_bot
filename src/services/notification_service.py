"""
通知服务
负责发送各种类型的通知
"""
import json
import hashlib
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import and_, func
import aiohttp
from loguru import logger

from ..config.database import SessionLocal
from ..config.settings import settings
from ..models.notification import Notification
from ..schemas.notification import (
    NotificationCreate, NotificationTriggerRequest, WeChatMessage,
    NotificationChannel, NotificationStatus, NotificationType
)


class NotificationService:
    """通知服务类"""
    
    def __init__(self):
        self.wechat_webhook_url = settings.wechat_webhook_url
        self.max_retry_count = 3
        self.dedup_cache = {}  # 简单的内存去重缓存
    
    async def send_notification(self, notification_data: NotificationCreate) -> bool:
        """发送通知"""
        db = SessionLocal()
        try:
            # 检查去重
            if notification_data.dedup_key and await self._is_duplicate(db, notification_data.dedup_key):
                logger.info(f"通知已去重跳过: {notification_data.dedup_key}")
                return True
            
            # 创建通知记录
            notification = Notification(
                type=notification_data.type,
                title=notification_data.title,
                content=notification_data.content,
                is_urgent=notification_data.is_urgent,
                channel=notification_data.channel,
                related_type=notification_data.related_type,
                related_id=notification_data.related_id,
                data=notification_data.data or {},
                dedup_key=notification_data.dedup_key,
                status=NotificationStatus.PENDING
            )
            
            db.add(notification)
            db.commit()
            db.refresh(notification)
            
            # 发送通知
            success = await self._send_by_channel(notification)
            
            # 更新发送状态
            if success:
                notification.status = NotificationStatus.SENT
                notification.sent_at = datetime.utcnow()
            else:
                notification.status = NotificationStatus.FAILED
                notification.error_message = "发送失败"
            
            db.commit()
            
            return success
            
        except Exception as e:
            logger.error(f"发送通知失败: {e}")
            if 'notification' in locals():
                notification.status = NotificationStatus.FAILED
                notification.error_message = str(e)
                db.commit()
            return False
        finally:
            db.close()
    
    async def send_by_template(self, template_request: NotificationTriggerRequest) -> bool:
        """使用模板发送通知"""
        try:
            # 从硬编码配置获取模板
            from ..config.notification_config import get_template
            
            template = get_template(template_request.template_name)
            
            # 渲染模板
            title = self._render_template(template.title_template, template_request.variables)
            content = self._render_template(template.content_template, template_request.variables)
            
            # 生成去重键
            dedup_key = template_request.dedup_key
            if template.dedup_enabled and not dedup_key:
                dedup_key = self._generate_dedup_key(
                    template.name, title, template_request.variables
                )
            
            # 创建通知请求
            notification_data = NotificationCreate(
                type=template.type,
                title=title,
                content=content,
                is_urgent=template_request.override_urgent or template.is_urgent,
                channel=template_request.override_channel or template.channel,
                related_type="template",
                related_id=template.name,  # 使用模板名称而不是数据库ID
                data={"template_name": template.name, "variables": template_request.variables},
                dedup_key=dedup_key
            )
            
            return await self.send_notification(notification_data)
            
        except ValueError as e:
            # 模板不存在的错误
            logger.error(f"通知模板不存在: {e}")
            return False
        except Exception as e:
            logger.error(f"使用模板发送通知失败: {e}")
            return False
    
    async def _send_by_channel(self, notification: Notification) -> bool:
        """根据渠道发送通知"""
        if notification.channel == NotificationChannel.WECHAT:
            return await self._send_wechat_message(notification)
        elif notification.channel == NotificationChannel.EMAIL:
            # TODO: 实现邮件发送
            logger.warning("邮件通知尚未实现")
            return False
        elif notification.channel == NotificationChannel.SMS:
            # TODO: 实现短信发送
            logger.warning("短信通知尚未实现")
            return False
        else:
            logger.error(f"不支持的通知渠道: {notification.channel}")
            return False
    
    async def _send_wechat_message(self, notification: Notification) -> bool:
        """发送企业微信消息"""
        if not self.wechat_webhook_url:
            logger.error("企业微信Webhook URL未配置")
            return False
        
        try:
            # 构造消息
            if notification.is_urgent:
                # 紧急消息使用醒目的格式
                message = WeChatMessage(
                    msgtype="markdown",
                    markdown={
                        "content": f"## 🚨 {notification.title}\n\n{notification.content}\n\n⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                    }
                )
            else:
                message = WeChatMessage(
                    msgtype="markdown", 
                    markdown={
                        "content": f"## {notification.title}\n\n{notification.content}\n\n⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                    }
                )
            
            # 发送HTTP请求
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.wechat_webhook_url,
                    json=message.dict(),
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        if result.get("errcode") == 0:
                            logger.info(f"企业微信通知发送成功: {notification.title}")
                            return True
                        else:
                            logger.error(f"企业微信接口返回错误: {result}")
                            return False
                    else:
                        logger.error(f"企业微信HTTP请求失败: {response.status}")
                        return False
        
        except Exception as e:
            logger.error(f"发送企业微信消息失败: {e}")
            return False
    
    async def _is_duplicate(self, db: Session, dedup_key: str) -> bool:
        """检查是否重复通知"""
        # 检查5分钟内是否有相同的去重键
        cutoff_time = datetime.utcnow() - timedelta(minutes=5)
        
        existing = db.query(Notification).filter(
            and_(
                Notification.dedup_key == dedup_key,
                Notification.created_at > cutoff_time,
                Notification.status == NotificationStatus.SENT
            )
        ).first()
        
        return existing is not None
    
    def _render_template(self, template: str, variables: Dict[str, Any]) -> str:
        """渲染模板"""
        try:
            # 处理双大括号模板格式 {{variable}} -> {variable}
            import re
            
            # 将 {{variable}} 替换为 {variable}
            processed_template = re.sub(r'\{\{(\w+)\}\}', r'{\1}', template)
            
            return processed_template.format(**variables)
        except KeyError as e:
            logger.error(f"模板变量缺失: {e}")
            logger.debug(f"可用变量: {list(variables.keys())}")
            return template
        except Exception as e:
            logger.error(f"模板渲染失败: {e}")
            return template
    
    def _generate_dedup_key(self, template_name: str, title: str, variables: Dict[str, Any]) -> str:
        """生成去重键"""
        # 使用模板名、标题和关键变量生成MD5哈希
        content = f"{template_name}:{title}:{json.dumps(variables, sort_keys=True)}"
        return hashlib.md5(content.encode()).hexdigest()
    
    async def retry_failed_notifications(self) -> int:
        """重试失败的通知"""
        db = SessionLocal()
        try:
            # 获取失败且重试次数未超限的通知
            failed_notifications = db.query(Notification).filter(
                and_(
                    Notification.status == NotificationStatus.FAILED,
                    Notification.retry_count < self.max_retry_count,
                    Notification.created_at > datetime.utcnow() - timedelta(hours=24)  # 只重试24小时内的
                )
            ).all()
            
            retry_count = 0
            
            for notification in failed_notifications:
                try:
                    # 重新发送
                    success = await self._send_by_channel(notification)
                    
                    notification.retry_count += 1
                    
                    if success:
                        notification.status = NotificationStatus.SENT
                        notification.sent_at = datetime.utcnow()
                        notification.error_message = None
                        logger.info(f"通知重试成功: {notification.id}")
                    else:
                        notification.error_message = f"重试失败 (第{notification.retry_count}次)"
                        logger.warning(f"通知重试失败: {notification.id}")
                    
                    retry_count += 1
                    
                except Exception as e:
                    notification.retry_count += 1
                    notification.error_message = str(e)
                    logger.error(f"通知重试异常: {notification.id}, {e}")
            
            db.commit()
            return retry_count
            
        except Exception as e:
            logger.error(f"重试失败通知异常: {e}")
            return 0
        finally:
            db.close()
    
    async def get_notification_stats(self) -> Dict[str, Any]:
        """获取通知统计信息"""
        db = SessionLocal()
        try:
            # 基础统计
            total = db.query(Notification).count()
            sent = db.query(Notification).filter(Notification.status == NotificationStatus.SENT).count()
            failed = db.query(Notification).filter(Notification.status == NotificationStatus.FAILED).count()
            pending = db.query(Notification).filter(Notification.status == NotificationStatus.PENDING).count()
            urgent = db.query(Notification).filter(Notification.is_urgent == True).count()
            
            # 今日统计
            today = datetime.utcnow().date()
            today_count = db.query(Notification).filter(
                func.date(Notification.created_at) == today
            ).count()
            
            # 按类型统计
            type_stats = {}
            for notification_type in NotificationType:
                count = db.query(Notification).filter(Notification.type == notification_type).count()
                if count > 0:
                    type_stats[notification_type.value] = count
            
            # 按渠道统计
            channel_stats = {}
            for channel in NotificationChannel:
                count = db.query(Notification).filter(Notification.channel == channel).count()
                if count > 0:
                    channel_stats[channel.value] = count
            
            # 成功率
            success_rate = (sent / total * 100) if total > 0 else 0
            
            return {
                "total_notifications": total,
                "sent_notifications": sent,
                "failed_notifications": failed,
                "pending_notifications": pending,
                "urgent_notifications": urgent,
                "today_notifications": today_count,
                "type_stats": type_stats,
                "channel_stats": channel_stats,
                "success_rate": round(success_rate, 2)
            }
            
        except Exception as e:
            logger.error(f"获取通知统计失败: {e}")
            return {}
        finally:
            db.close()


# 全局通知服务实例
notification_service = NotificationService()