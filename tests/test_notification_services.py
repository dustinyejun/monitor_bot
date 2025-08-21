"""
通知服务测试
"""
import pytest
import asyncio
from unittest.mock import patch, AsyncMock, MagicMock
from datetime import datetime, timedelta

from src.services.notification_service import NotificationService
from src.services.notification_template_service import NotificationTemplateService
from src.services.notification_engine import NotificationEngine
from src.services.rate_limiter import RateLimiter, DeduplicationService
from src.schemas.notification import (
    NotificationCreate, NotificationTriggerRequest,
    NotificationTemplateCreate, NotificationRuleCreate,
    NotificationType, NotificationChannel, NotificationStatus
)


class TestNotificationService:
    """通知服务测试"""
    
    @pytest.fixture
    def notification_service(self):
        return NotificationService()
    
    @pytest.fixture
    def mock_notification_data(self):
        return NotificationCreate(
            type=NotificationType.SYSTEM,
            title="测试通知",
            content="这是一条测试通知",
            is_urgent=False,
            channel=NotificationChannel.WECHAT,
            data={"test": True}
        )
    
    @pytest.mark.asyncio
    async def test_send_notification_success(self, notification_service, mock_notification_data):
        """测试成功发送通知"""
        with patch('src.services.notification_service.SessionLocal') as mock_session:
            with patch.object(notification_service, '_send_by_channel', return_value=True):
                with patch.object(notification_service, '_is_duplicate', return_value=False):
                    mock_db = MagicMock()
                    mock_session.return_value = mock_db
                    
                    result = await notification_service.send_notification(mock_notification_data)
                    
                    assert result is True
                    mock_db.add.assert_called_once()
                    mock_db.commit.assert_called()
    
    @pytest.mark.asyncio
    async def test_send_notification_duplicate(self, notification_service, mock_notification_data):
        """测试发送重复通知"""
        mock_notification_data.dedup_key = "test_dedup_key"
        
        with patch('src.services.notification_service.SessionLocal') as mock_session:
            with patch.object(notification_service, '_is_duplicate', return_value=True):
                mock_db = MagicMock()
                mock_session.return_value = mock_db
                
                result = await notification_service.send_notification(mock_notification_data)
                
                assert result is True  # 去重情况下返回True
                mock_db.add.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_send_wechat_message_success(self, notification_service):
        """测试成功发送微信消息"""
        with patch('aiohttp.ClientSession') as mock_session:
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.json = AsyncMock(return_value={"errcode": 0})
            
            mock_session.return_value.__aenter__.return_value.post.return_value.__aenter__.return_value = mock_response
            
            mock_notification = MagicMock()
            mock_notification.title = "测试标题"
            mock_notification.content = "测试内容"
            mock_notification.is_urgent = False
            
            result = await notification_service._send_wechat_message(mock_notification)
            
            assert result is True
    
    @pytest.mark.asyncio
    async def test_send_wechat_message_no_webhook(self, notification_service):
        """测试无Webhook URL时的处理"""
        notification_service.wechat_webhook_url = None
        
        mock_notification = MagicMock()
        result = await notification_service._send_wechat_message(mock_notification)
        
        assert result is False


class TestNotificationTemplateService:
    """通知模板服务测试"""
    
    @pytest.fixture
    def template_service(self):
        return NotificationTemplateService()
    
    @pytest.fixture
    def mock_template_data(self):
        return NotificationTemplateCreate(
            name="test_template",
            type=NotificationType.TWITTER,
            title_template="测试标题: {title}",
            content_template="测试内容: {content}",
            is_active=True,
            variables={"title": "标题", "content": "内容"}
        )
    
    def test_create_template_success(self, template_service, mock_template_data):
        """测试成功创建模板"""
        with patch('src.services.notification_template_service.SessionLocal') as mock_session:
            mock_db = MagicMock()
            mock_session.return_value = mock_db
            
            # 模拟不存在重复模板
            mock_db.query.return_value.filter.return_value.first.return_value = None
            
            # 模拟创建的模板
            mock_template = MagicMock()
            mock_template.name = "test_template"
            mock_db.add.return_value = None
            mock_db.refresh.return_value = None
            
            with patch('src.schemas.notification.NotificationTemplateResponse.from_orm') as mock_from_orm:
                mock_from_orm.return_value = MagicMock()
                
                result = template_service.create_template(mock_template_data)
                
                assert result is not None
                mock_db.add.assert_called_once()
                mock_db.commit.assert_called_once()
    
    def test_create_template_duplicate_name(self, template_service, mock_template_data):
        """测试创建重复名称模板"""
        with patch('src.services.notification_template_service.SessionLocal') as mock_session:
            mock_db = MagicMock()
            mock_session.return_value = mock_db
            
            # 模拟存在重复模板
            mock_db.query.return_value.filter.return_value.first.return_value = MagicMock()
            
            with pytest.raises(ValueError, match="模板名称已存在"):
                template_service.create_template(mock_template_data)


class TestNotificationEngine:
    """通知引擎测试"""
    
    @pytest.fixture
    def notification_engine(self):
        return NotificationEngine()
    
    def test_evaluate_conditions_simple(self, notification_engine):
        """测试简单条件评估"""
        data = {"amount": 100, "type": "test"}
        conditions = {
            "field": "amount",
            "operator": "gt",
            "value": 50
        }
        
        result = notification_engine._evaluate_conditions(data, conditions)
        assert result is True
    
    def test_evaluate_conditions_and_logic(self, notification_engine):
        """测试AND逻辑条件"""
        data = {"amount": 100, "type": "important"}
        conditions = {
            "and": [
                {"field": "amount", "operator": "gt", "value": 50},
                {"field": "type", "operator": "eq", "value": "important"}
            ]
        }
        
        result = notification_engine._evaluate_conditions(data, conditions)
        assert result is True
    
    def test_evaluate_conditions_or_logic(self, notification_engine):
        """测试OR逻辑条件"""
        data = {"amount": 30, "type": "important"}
        conditions = {
            "or": [
                {"field": "amount", "operator": "gt", "value": 50},
                {"field": "type", "operator": "eq", "value": "important"}
            ]
        }
        
        result = notification_engine._evaluate_conditions(data, conditions)
        assert result is True
    
    def test_get_nested_value(self, notification_engine):
        """测试获取嵌套字段值"""
        data = {
            "user": {
                "profile": {
                    "name": "test_user"
                }
            },
            "amount": 100
        }
        
        # 测试嵌套字段
        result = notification_engine._get_nested_value(data, "user.profile.name")
        assert result == "test_user"
        
        # 测试简单字段
        result = notification_engine._get_nested_value(data, "amount")
        assert result == 100
        
        # 测试不存在的字段
        result = notification_engine._get_nested_value(data, "nonexistent.field")
        assert result is None
    
    @pytest.mark.asyncio
    async def test_trigger_notification(self, notification_engine):
        """测试触发通知"""
        variables = {"title": "测试", "content": "内容"}
        
        with patch('src.services.notification_engine.notification_service') as mock_service:
            mock_service.send_by_template = AsyncMock(return_value=True)
            
            result = await notification_engine._trigger_notification("test_template", variables)
            
            assert result is True
            mock_service.send_by_template.assert_called_once()


class TestRateLimiter:
    """限流器测试"""
    
    @pytest.fixture
    def rate_limiter(self):
        return RateLimiter()
    
    def test_memory_cache_rate_limit(self, rate_limiter):
        """测试内存缓存限流"""
        key = "test_key"
        max_count = 3
        window_seconds = 60
        
        # 前3次应该通过
        for i in range(3):
            result = rate_limiter._check_memory_cache(key, max_count, window_seconds)
            assert result is True
        
        # 第4次应该被限流
        result = rate_limiter._check_memory_cache(key, max_count, window_seconds)
        assert result is False
    
    @pytest.mark.asyncio
    async def test_database_rate_limit_success(self, rate_limiter):
        """测试数据库限流通过"""
        with patch('src.services.rate_limiter.SessionLocal') as mock_session:
            mock_db = MagicMock()
            mock_session.return_value = mock_db
            mock_db.query.return_value.filter.return_value.count.return_value = 2
            
            result = await rate_limiter._check_database_limit("test_key", 5, 300)
            
            assert result is True
    
    @pytest.mark.asyncio
    async def test_database_rate_limit_blocked(self, rate_limiter):
        """测试数据库限流阻止"""
        with patch('src.services.rate_limiter.SessionLocal') as mock_session:
            mock_db = MagicMock()
            mock_session.return_value = mock_db
            mock_db.query.return_value.filter.return_value.count.return_value = 5
            
            result = await rate_limiter._check_database_limit("test_key", 3, 300)
            
            assert result is False


class TestDeduplicationService:
    """去重服务测试"""
    
    @pytest.fixture
    def dedup_service(self):
        return DeduplicationService()
    
    @pytest.mark.asyncio
    async def test_check_duplicate_new(self, dedup_service):
        """测试检查新的去重键"""
        with patch.object(dedup_service, '_check_database_duplicate', return_value=False):
            result = await dedup_service.check_duplicate("new_key", use_database=True)
            assert result is False
    
    @pytest.mark.asyncio
    async def test_check_duplicate_existing(self, dedup_service):
        """测试检查已存在的去重键"""
        # 先添加到缓存
        dedup_service._add_to_cache("existing_key")
        
        result = await dedup_service.check_duplicate("existing_key", use_database=False)
        assert result is True
    
    @pytest.mark.asyncio
    async def test_database_duplicate_check(self, dedup_service):
        """测试数据库去重检查"""
        with patch('src.services.rate_limiter.SessionLocal') as mock_session:
            mock_db = MagicMock()
            mock_session.return_value = mock_db
            
            # 模拟找到重复记录
            mock_db.query.return_value.filter.return_value.first.return_value = MagicMock()
            
            result = await dedup_service._check_database_duplicate("test_key", 300)
            
            assert result is True
    
    def test_cache_size_limit(self, dedup_service):
        """测试缓存大小限制"""
        # 设置较小的缓存大小用于测试
        dedup_service.max_cache_size = 5
        
        # 添加超过限制的项目
        for i in range(10):
            dedup_service._add_to_cache(f"key_{i}")
        
        # 检查缓存大小是否被限制
        assert len(dedup_service.memory_cache) <= dedup_service.max_cache_size


# 集成测试
class TestNotificationIntegration:
    """通知系统集成测试"""
    
    @pytest.mark.asyncio
    async def test_complete_notification_flow(self):
        """测试完整的通知流程"""
        # 这个测试需要数据库连接，在实际环境中运行
        pass
    
    @pytest.mark.asyncio
    async def test_template_and_rule_integration(self):
        """测试模板和规则集成"""
        # 这个测试需要数据库连接，在实际环境中运行
        pass