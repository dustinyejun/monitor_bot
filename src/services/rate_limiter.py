"""
限流服务
提供通知限流功能
"""
import json
import time
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_, func
from loguru import logger

from ..config.database import SessionLocal
from ..models.notification import Notification


class RateLimiter:
    """通知限流器"""
    
    def __init__(self):
        self.memory_cache = {}  # 内存缓存用于快速检查
        self.cache_expire_seconds = 3600  # 缓存过期时间1小时
    
    async def check_rate_limit(
        self,
        key: str,
        max_count: int,
        window_seconds: int,
        use_database: bool = True
    ) -> bool:
        """
        检查是否触发限流
        
        Args:
            key: 限流键（如规则名、用户ID等）
            max_count: 时间窗口内最大允许次数
            window_seconds: 时间窗口大小（秒）
            use_database: 是否使用数据库检查（更准确但较慢）
            
        Returns:
            True表示允许通过，False表示被限流
        """
        try:
            # 优先使用内存缓存进行快速检查
            if not use_database:
                return self._check_memory_cache(key, max_count, window_seconds)
            
            # 使用数据库进行精确检查
            return await self._check_database_limit(key, max_count, window_seconds)
        
        except Exception as e:
            logger.error(f"检查限流失败 {key}: {e}")
            return True  # 失败时允许通过
    
    def _check_memory_cache(self, key: str, max_count: int, window_seconds: int) -> bool:
        """内存缓存限流检查"""
        current_time = time.time()
        
        # 清理过期缓存
        self._cleanup_expired_cache(current_time)
        
        # 获取或创建缓存记录
        if key not in self.memory_cache:
            self.memory_cache[key] = {
                "timestamps": [],
                "last_access": current_time
            }
        
        cache_record = self.memory_cache[key]
        timestamps = cache_record["timestamps"]
        
        # 移除超出时间窗口的记录
        cutoff_time = current_time - window_seconds
        timestamps[:] = [ts for ts in timestamps if ts > cutoff_time]
        
        # 检查是否超出限制
        if len(timestamps) >= max_count:
            logger.warning(f"触发内存缓存限流: {key}, 当前次数: {len(timestamps)}/{max_count}")
            return False
        
        # 记录本次访问
        timestamps.append(current_time)
        cache_record["last_access"] = current_time
        
        return True
    
    async def _check_database_limit(self, key: str, max_count: int, window_seconds: int) -> bool:
        """数据库限流检查"""
        db = SessionLocal()
        try:
            cutoff_time = datetime.utcnow() - timedelta(seconds=window_seconds)
            
            # 查询时间窗口内的通知数量
            count = db.query(Notification).filter(
                and_(
                    Notification.data.op('->>')('rate_limit_key') == key,
                    Notification.created_at > cutoff_time,
                    Notification.status.in_(["sent", "pending"])
                )
            ).count()
            
            if count >= max_count:
                logger.warning(f"触发数据库限流: {key}, 当前次数: {count}/{max_count}")
                return False
            
            return True
        
        finally:
            db.close()
    
    def _cleanup_expired_cache(self, current_time: float):
        """清理过期的内存缓存"""
        expired_keys = []
        
        for key, record in self.memory_cache.items():
            if current_time - record["last_access"] > self.cache_expire_seconds:
                expired_keys.append(key)
        
        for key in expired_keys:
            del self.memory_cache[key]
    
    async def record_notification(self, key: str, notification_id: int):
        """记录通知发送（用于限流统计）"""
        try:
            db = SessionLocal()
            try:
                # 更新通知记录的限流键
                notification = db.query(Notification).filter(
                    Notification.id == notification_id
                ).first()
                
                if notification and notification.data:
                    if isinstance(notification.data, str):
                        data = json.loads(notification.data)
                    else:
                        data = notification.data or {}
                    
                    data["rate_limit_key"] = key
                    notification.data = data
                    db.commit()
            
            finally:
                db.close()
        
        except Exception as e:
            logger.error(f"记录通知限流信息失败: {e}")
    
    async def get_rate_limit_stats(self, key: str, window_seconds: int = 3600) -> Dict[str, Any]:
        """获取限流统计信息"""
        try:
            db = SessionLocal()
            try:
                cutoff_time = datetime.utcnow() - timedelta(seconds=window_seconds)
                
                # 统计时间窗口内的通知
                notifications = db.query(Notification).filter(
                    and_(
                        Notification.data.op('->>')('rate_limit_key') == key,
                        Notification.created_at > cutoff_time
                    )
                ).all()
                
                # 按状态统计
                stats = {
                    "key": key,
                    "window_seconds": window_seconds,
                    "total_count": len(notifications),
                    "sent_count": sum(1 for n in notifications if n.status == "sent"),
                    "pending_count": sum(1 for n in notifications if n.status == "pending"),
                    "failed_count": sum(1 for n in notifications if n.status == "failed"),
                    "earliest_time": None,
                    "latest_time": None
                }
                
                if notifications:
                    times = [n.created_at for n in notifications]
                    stats["earliest_time"] = min(times).isoformat()
                    stats["latest_time"] = max(times).isoformat()
                
                return stats
            
            finally:
                db.close()
        
        except Exception as e:
            logger.error(f"获取限流统计失败: {e}")
            return {"error": str(e)}
    
    def reset_memory_cache(self, key: Optional[str] = None):
        """重置内存缓存"""
        if key:
            self.memory_cache.pop(key, None)
            logger.info(f"已重置限流缓存: {key}")
        else:
            self.memory_cache.clear()
            logger.info("已重置所有限流缓存")


class DeduplicationService:
    """去重服务"""
    
    def __init__(self):
        self.memory_cache = set()  # 简单的内存去重缓存
        self.max_cache_size = 10000  # 最大缓存大小
    
    async def check_duplicate(
        self,
        dedup_key: str,
        window_seconds: int = 300,
        use_database: bool = True
    ) -> bool:
        """
        检查是否重复通知
        
        Args:
            dedup_key: 去重键
            window_seconds: 去重时间窗口
            use_database: 是否使用数据库检查
            
        Returns:
            True表示重复，False表示不重复
        """
        try:
            # 优先使用内存缓存
            if dedup_key in self.memory_cache:
                logger.debug(f"内存缓存命中，通知重复: {dedup_key}")
                return True
            
            # 使用数据库检查
            if use_database:
                is_duplicate = await self._check_database_duplicate(dedup_key, window_seconds)
                if is_duplicate:
                    return True
            
            # 记录到内存缓存
            self._add_to_cache(dedup_key)
            return False
        
        except Exception as e:
            logger.error(f"检查去重失败: {e}")
            return False  # 失败时不去重
    
    async def _check_database_duplicate(self, dedup_key: str, window_seconds: int) -> bool:
        """数据库去重检查"""
        db = SessionLocal()
        try:
            cutoff_time = datetime.utcnow() - timedelta(seconds=window_seconds)
            
            # 查找相同去重键的已发送通知
            existing = db.query(Notification).filter(
                and_(
                    Notification.dedup_key == dedup_key,
                    Notification.created_at > cutoff_time,
                    Notification.status == "sent"
                )
            ).first()
            
            return existing is not None
        
        finally:
            db.close()
    
    def _add_to_cache(self, dedup_key: str):
        """添加到内存缓存"""
        # 防止缓存过大
        if len(self.memory_cache) >= self.max_cache_size:
            # 移除一半的缓存项（简单的LRU策略）
            items_to_remove = list(self.memory_cache)[:self.max_cache_size // 2]
            for item in items_to_remove:
                self.memory_cache.discard(item)
        
        self.memory_cache.add(dedup_key)
    
    def clear_cache(self):
        """清空缓存"""
        self.memory_cache.clear()
        logger.info("已清空去重缓存")


# 全局实例
rate_limiter = RateLimiter()
deduplication_service = DeduplicationService()