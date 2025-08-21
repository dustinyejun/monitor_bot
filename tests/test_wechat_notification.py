"""
企业微信通知测试用例
测试企业微信通知的发送功能
"""
import pytest
import asyncio
from unittest.mock import patch, AsyncMock, MagicMock
from datetime import datetime

from src.services.notification_service import NotificationService
from src.schemas.notification import NotificationCreate, NotificationTriggerRequest
from src.schemas.notification import NotificationType, NotificationChannel


class TestWeChatNotification:
    """企业微信通知测试"""
    
    @pytest.fixture
    def notification_service(self):
        """创建通知服务实例"""
        service = NotificationService()
        service.wechat_webhook_url = "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=test_key"
        return service
    
    @pytest.fixture
    def sample_notification(self):
        """样例通知数据"""
        return NotificationCreate(
            type=NotificationType.TWITTER,
            title="🚨 CA地址推文提醒",
            content="""### 📱 用户: elonmusk
**推文内容**: 发现新的代币合约地址

**CA地址**: `0x1234567890abcdef`

**推文链接**: https://twitter.com/elonmusk/status/123456789

**发布时间**: 2025-08-20 10:30:00""",
            is_urgent=True,
            channel=NotificationChannel.WECHAT,
            data={
                "username": "elonmusk",
                "ca_address": "0x1234567890abcdef",
                "tweet_id": "123456789"
            }
        )
    
    @pytest.mark.asyncio
    async def test_send_wechat_message_success(self, notification_service, sample_notification):
        """测试成功发送企业微信消息"""
        # Mock HTTP响应
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={"errcode": 0, "errmsg": "ok"})
        
        with patch('aiohttp.ClientSession') as mock_session:
            mock_session.return_value.__aenter__.return_value.post.return_value.__aenter__.return_value = mock_response
            
            # 发送通知
            result = await notification_service.send_notification(sample_notification)
            
            assert result is True
            
            # 验证HTTP请求被调用
            mock_session.return_value.__aenter__.return_value.post.assert_called_once()
            call_args = mock_session.return_value.__aenter__.return_value.post.call_args
            
            # 验证请求URL
            assert "qyapi.weixin.qq.com" in call_args[0][0]
            
            # 验证请求数据
            json_data = call_args[1]['json']
            assert json_data['msgtype'] == 'markdown'
            assert '🚨' in json_data['markdown']['content']
            assert 'elonmusk' in json_data['markdown']['content']
    
    @pytest.mark.asyncio
    async def test_send_wechat_urgent_message(self, notification_service):
        """测试发送紧急企业微信消息的格式"""
        urgent_notification = NotificationCreate(
            type=NotificationType.SOLANA,
            title="💰 大额交易提醒",
            content="发现大额Solana交易：$50,000 USD",
            is_urgent=True,
            channel=NotificationChannel.WECHAT
        )
        
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={"errcode": 0})
        
        with patch('aiohttp.ClientSession') as mock_session:
            mock_session.return_value.__aenter__.return_value.post.return_value.__aenter__.return_value = mock_response
            
            result = await notification_service.send_notification(urgent_notification)
            
            assert result is True
            
            # 验证紧急消息格式
            call_args = mock_session.return_value.__aenter__.return_value.post.call_args
            json_data = call_args[1]['json']
            
            # 紧急消息应该包含🚨标识
            assert '🚨' in json_data['markdown']['content']
            assert '💰' in json_data['markdown']['content']
    
    @pytest.mark.asyncio
    async def test_send_wechat_message_api_error(self, notification_service, sample_notification):
        """测试企业微信API返回错误的情况"""
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={
            "errcode": 93000, 
            "errmsg": "invalid webhook url"
        })
        
        with patch('aiohttp.ClientSession') as mock_session:
            mock_session.return_value.__aenter__.return_value.post.return_value.__aenter__.return_value = mock_response
            
            result = await notification_service.send_notification(sample_notification)
            
            assert result is False
    
    @pytest.mark.asyncio
    async def test_send_wechat_message_http_error(self, notification_service, sample_notification):
        """测试HTTP请求失败的情况"""
        mock_response = AsyncMock()
        mock_response.status = 500
        
        with patch('aiohttp.ClientSession') as mock_session:
            mock_session.return_value.__aenter__.return_value.post.return_value.__aenter__.return_value = mock_response
            
            result = await notification_service.send_notification(sample_notification)
            
            assert result is False
    
    @pytest.mark.asyncio
    async def test_send_wechat_message_timeout(self, notification_service, sample_notification):
        """测试网络超时的情况"""
        with patch('aiohttp.ClientSession') as mock_session:
            mock_session.return_value.__aenter__.return_value.post.side_effect = asyncio.TimeoutError()
            
            result = await notification_service.send_notification(sample_notification)
            
            assert result is False
    
    @pytest.mark.asyncio
    async def test_send_wechat_no_webhook_url(self, sample_notification):
        """测试没有配置Webhook URL的情况"""
        service = NotificationService()
        service.wechat_webhook_url = None  # 未配置
        
        result = await service.send_notification(sample_notification)
        
        assert result is False
    
    @pytest.mark.asyncio
    async def test_send_template_notification(self, notification_service):
        """测试使用模板发送企业微信通知"""
        # Mock模板服务
        with patch('src.services.notification_service.SessionLocal') as mock_session:
            # Mock数据库查询
            mock_db = MagicMock()
            mock_session.return_value = mock_db
            
            # Mock模板数据
            mock_template = MagicMock()
            mock_template.name = "twitter_ca_alert"
            mock_template.type = "twitter"
            mock_template.title_template = "🚨 CA地址推文提醒"
            mock_template.content_template = """### 📱 用户: {username}
**推文内容**: {content}
**CA地址**: `{ca_addresses}`
**推文链接**: {tweet_url}
**发布时间**: {tweet_created_at}"""
            mock_template.is_active = True
            mock_template.is_urgent = True
            mock_template.channel = "wechat"
            mock_template.dedup_enabled = True
            mock_template.id = 1
            
            mock_db.query.return_value.filter.return_value.first.return_value = mock_template
            mock_db.query.return_value.filter.return_value.first.return_value = None  # 去重检查
            
            # Mock通知记录
            mock_notification = MagicMock()
            mock_notification.id = 1
            mock_db.add.return_value = None
            mock_db.refresh.return_value = None
            
            # Mock HTTP响应
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.json = AsyncMock(return_value={"errcode": 0})
            
            with patch('aiohttp.ClientSession') as mock_http_session:
                mock_http_session.return_value.__aenter__.return_value.post.return_value.__aenter__.return_value = mock_response
                
                # 准备模板请求
                template_request = NotificationTriggerRequest(
                    template_name="twitter_ca_alert",
                    variables={
                        "username": "elonmusk",
                        "content": "发现新代币合约",
                        "ca_addresses": "0x1234567890abcdef",
                        "tweet_url": "https://twitter.com/elonmusk/status/123456",
                        "tweet_created_at": "2025-08-20 10:30:00"
                    }
                )
                
                result = await notification_service.send_by_template(template_request)
                
                assert result is True
                
                # 验证模板变量被正确替换
                call_args = mock_http_session.return_value.__aenter__.return_value.post.call_args
                json_data = call_args[1]['json']
                content = json_data['markdown']['content']
                
                assert "elonmusk" in content
                assert "0x1234567890abcdef" in content
                assert "twitter.com" in content


class TestWeChatMessageFormat:
    """企业微信消息格式测试"""
    
    def test_markdown_message_format(self):
        """测试Markdown消息格式"""
        from src.schemas.notification import WeChatMessage
        
        message = WeChatMessage(
            msgtype="markdown",
            markdown={
                "content": "## 标题\n\n内容\n\n时间: 2025-08-20"
            }
        )
        
        assert message.msgtype == "markdown"
        assert "标题" in message.markdown["content"]
        assert message.text is None
    
    def test_text_message_format(self):
        """测试文本消息格式"""
        from src.schemas.notification import WeChatMessage
        
        message = WeChatMessage(
            msgtype="text",
            text={
                "content": "这是一条文本消息"
            }
        )
        
        assert message.msgtype == "text"
        assert message.text["content"] == "这是一条文本消息"
        assert message.markdown is None
    
    def test_invalid_msgtype(self):
        """测试无效的消息类型"""
        from src.schemas.notification import WeChatMessage
        from pydantic import ValidationError
        
        with pytest.raises(ValidationError):
            WeChatMessage(
                msgtype="invalid_type",
                text={"content": "test"}
            )


# 真实企业微信API测试（需要有效的Webhook URL）
class TestRealWeChatAPI:
    """真实企业微信API测试"""
    
    @pytest.mark.asyncio
    @pytest.mark.skipif(
        not pytest.config.getoption("--run-real-api", default=False),
        reason="需要 --run-real-api 参数才运行真实API测试"
    )
    async def test_real_wechat_notification(self):
        """测试真实的企业微信通知发送"""
        import os
        
        # 从环境变量获取真实的Webhook URL
        webhook_url = os.getenv("WECHAT_WEBHOOK_URL")
        
        if not webhook_url:
            pytest.skip("需要设置 WECHAT_WEBHOOK_URL 环境变量")
        
        service = NotificationService()
        service.wechat_webhook_url = webhook_url
        
        test_notification = NotificationCreate(
            type=NotificationType.SYSTEM,
            title="🧪 系统测试通知",
            content="""### 📋 测试信息
**测试时间**: {current_time}
**测试类型**: 企业微信通知功能测试
**状态**: 正常

这是一条来自监控机器人的测试通知，用于验证企业微信通知功能是否正常工作。

如果您收到这条消息，说明通知系统运行正常！ ✅""".format(
                current_time=datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            ),
            is_urgent=False,
            channel=NotificationChannel.WECHAT,
            data={"test": True, "timestamp": datetime.now().isoformat()}
        )
        
        try:
            result = await service.send_notification(test_notification)
            assert result is True, "真实企业微信通知发送失败"
            print("✅ 真实企业微信通知发送成功！")
        
        except Exception as e:
            pytest.fail(f"真实企业微信通知发送异常: {str(e)}")
    
    @pytest.mark.asyncio 
    @pytest.mark.skipif(
        not pytest.config.getoption("--run-real-api", default=False),
        reason="需要 --run-real-api 参数才运行真实API测试"
    )
    async def test_real_template_notification(self):
        """测试真实的模板通知发送"""
        import os
        
        webhook_url = os.getenv("WECHAT_WEBHOOK_URL")
        if not webhook_url:
            pytest.skip("需要设置 WECHAT_WEBHOOK_URL 环境变量")
        
        # 需要先初始化默认模板
        from src.services.notification_template_service import init_default_templates
        
        try:
            init_default_templates()
        except Exception:
            pass  # 模板可能已存在
        
        service = NotificationService()
        service.wechat_webhook_url = webhook_url
        
        template_request = NotificationTriggerRequest(
            template_name="system_status_alert",
            variables={
                "component": "企业微信通知系统",
                "status": "测试正常",
                "message": "这是使用模板发送的测试通知",
                "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
        )
        
        try:
            result = await service.send_by_template(template_request)
            assert result is True, "真实模板通知发送失败"
            print("✅ 真实模板通知发送成功！")
        
        except Exception as e:
            pytest.fail(f"真实模板通知发送异常: {str(e)}")


# 性能测试
class TestWeChatPerformance:
    """企业微信通知性能测试"""
    
    @pytest.mark.asyncio
    async def test_concurrent_notifications(self):
        """测试并发通知发送"""
        service = NotificationService()
        service.wechat_webhook_url = "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=test"
        
        # Mock HTTP响应
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={"errcode": 0})
        
        with patch('aiohttp.ClientSession') as mock_session:
            mock_session.return_value.__aenter__.return_value.post.return_value.__aenter__.return_value = mock_response
            
            # 创建多个通知任务
            notifications = []
            for i in range(10):
                notification = NotificationCreate(
                    type=NotificationType.SYSTEM,
                    title=f"测试通知 {i}",
                    content=f"这是第 {i} 条测试通知",
                    channel=NotificationChannel.WECHAT
                )
                notifications.append(service.send_notification(notification))
            
            # 并发执行
            results = await asyncio.gather(*notifications, return_exceptions=True)
            
            # 验证结果
            success_count = sum(1 for r in results if r is True)
            assert success_count == 10, f"并发通知发送成功率: {success_count}/10"


if __name__ == "__main__":
    # 可以直接运行此文件进行测试
    pytest.main([__file__, "-v"])