"""
推特服务相关的单元测试
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime

from src.services.twitter_client import TwitterClient, TwitterUserInfo, TwitterTweetInfo, TwitterAPIError
from src.services.twitter_analyzer import TwitterAnalyzer, ContractAddress, ContractAddressType, AnalysisResult
from src.services.twitter_monitor import TwitterMonitorService

# 配置pytest-asyncio
pytest_plugins = ('pytest_asyncio',)


class TestTwitterClient:
    """Twitter客户端测试"""
    
    @pytest.fixture
    def client(self):
        """创建测试客户端"""
        return TwitterClient("test_bearer_token")
        
    @pytest.mark.asyncio
    async def test_get_user_by_username_success(self, client):
        """测试成功获取用户信息"""
        mock_response = {
            "data": {
                "id": "123456789",
                "username": "testuser",
                "name": "Test User",
                "description": "Test description",
                "public_metrics": {
                    "followers_count": 1000,
                    "following_count": 500
                },
                "created_at": "2020-01-01T00:00:00.000Z"
            }
        }
        
        with patch.object(client, '_make_request', new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response
            
            async with client:
                result = await client.get_user_by_username("testuser")
                
            assert result is not None
            assert result.id == "123456789"
            assert result.username == "testuser"
            assert result.name == "Test User"
            
    @pytest.mark.asyncio
    async def test_get_user_by_username_not_found(self, client):
        """测试用户不存在"""
        mock_response = {"errors": [{"title": "Not Found Error"}]}
        
        with patch.object(client, '_make_request', new_callable=AsyncMock) as mock_request:
            mock_request.side_effect = TwitterAPIError("User not found", 404)
            
            async with client:
                result = await client.get_user_by_username("nonexistentuser")
                
            assert result is None
            
    @pytest.mark.asyncio
    async def test_get_user_tweets_success(self, client):
        """测试成功获取用户推文"""
        mock_response = {
            "data": [
                {
                    "id": "tweet123",
                    "text": "Test tweet content with CA: 0x1234567890123456789012345678901234567890",
                    "created_at": "2024-01-01T12:00:00.000Z",
                    "public_metrics": {
                        "like_count": 10,
                        "retweet_count": 5
                    }
                }
            ]
        }
        
        with patch.object(client, '_make_request', new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response
            
            async with client:
                result = await client.get_user_tweets("123456789")
                
            assert len(result) == 1
            assert result[0].id == "tweet123"
            assert "CA:" in result[0].text
            
    @pytest.mark.asyncio
    async def test_rate_limit_handling(self, client):
        """测试速率限制处理"""
        with patch.object(client, '_make_request', new_callable=AsyncMock) as mock_request:
            mock_request.side_effect = TwitterAPIError("Rate limit exceeded", 429)
            
            async with client:
                with pytest.raises(TwitterAPIError) as exc_info:
                    await client.get_user_by_username("testuser")
                    
                assert exc_info.value.status_code == 429


class TestTwitterAnalyzer:
    """推特分析器测试"""
    
    @pytest.fixture
    def analyzer(self):
        """创建测试分析器"""
        return TwitterAnalyzer()
        
    def test_ethereum_address_detection(self, analyzer):
        """测试以太坊地址识别"""
        tweet_text = "New token launch! CA: 0x1234567890123456789012345678901234567890"
        result = analyzer.analyze_tweet(tweet_text)
        
        assert result.has_ca is True
        assert len(result.ca_addresses) == 1
        assert result.ca_addresses[0].type == ContractAddressType.ETHEREUM
        assert result.ca_addresses[0].address == "0x1234567890123456789012345678901234567890"
        
    def test_solana_address_detection(self, analyzer):
        """测试Solana地址识别"""
        tweet_text = "Check out this SOL gem: EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"
        result = analyzer.analyze_tweet(tweet_text)
        
        assert result.has_ca is True
        assert len(result.ca_addresses) == 1
        assert result.ca_addresses[0].type == ContractAddressType.SOLANA
        
    def test_bsc_address_detection(self, analyzer):
        """测试BSC地址识别"""
        tweet_text = "BSC token pumping! 0x1234567890123456789012345678901234567890 on PancakeSwap"
        result = analyzer.analyze_tweet(tweet_text)
        
        assert result.has_ca is True
        assert len(result.ca_addresses) == 1
        assert result.ca_addresses[0].type == ContractAddressType.BSC
        
    def test_multiple_addresses(self, analyzer):
        """测试多个地址识别"""
        tweet_text = """
        ETH: 0x1234567890123456789012345678901234567890
        SOL: EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v
        """
        result = analyzer.analyze_tweet(tweet_text)
        
        assert result.has_ca is True
        assert len(result.ca_addresses) == 2
        
    def test_false_positive_filtering(self, analyzer):
        """测试误报过滤"""
        tweet_text = "Follow me on Twitter: https://twitter.com/username"
        result = analyzer.analyze_tweet(tweet_text)
        
        assert result.has_ca is False
        assert len(result.ca_addresses) == 0
        
    def test_keyword_detection(self, analyzer):
        """测试关键词识别"""
        tweet_text = "New gem launching to the moon 🚀 Buy now!"
        result = analyzer.analyze_tweet(tweet_text)
        
        assert 'gem' in result.keywords_found
        assert 'moon' in result.keywords_found
        assert 'buy' in result.keywords_found
        
    def test_risk_score_calculation(self, analyzer):
        """测试风险评分计算"""
        # 高风险推文
        high_risk_text = "Scam token pumping! Quick money! 100x potential!"
        high_risk_result = analyzer.analyze_tweet(high_risk_text)
        
        # 正常推文
        normal_text = "Announcing our new DeFi project with solid tokenomics"
        normal_result = analyzer.analyze_tweet(normal_text)
        
        assert high_risk_result.risk_score > normal_result.risk_score
        assert high_risk_result.risk_score > 0.3
        
    def test_confidence_calculation(self, analyzer):
        """测试置信度计算"""
        # 高置信度（包含CA关键词）
        high_conf_text = "Contract address: 0x1234567890123456789012345678901234567890"
        high_conf_result = analyzer.analyze_tweet(high_conf_text)
        
        # 低置信度（只是随机字符串）
        low_conf_text = "Random text 0x1234567890123456789012345678901234567890 more text"
        low_conf_result = analyzer.analyze_tweet(low_conf_text)
        
        if high_conf_result.has_ca and low_conf_result.has_ca:
            assert high_conf_result.ca_addresses[0].confidence > low_conf_result.ca_addresses[0].confidence


class TestTwitterMonitorService:
    """推特监控服务测试"""
    
    @pytest.fixture
    def monitor_service(self):
        """创建测试监控服务"""
        return TwitterMonitorService()
        
    def test_add_user(self, monitor_service):
        """测试添加用户"""
        with patch('src.services.twitter_monitor.get_db') as mock_get_db:
            mock_db = Mock()
            mock_get_db.return_value.__enter__.return_value = mock_db
            mock_db.execute.return_value.scalar_one_or_none.return_value = None
            
            # 模拟创建的用户对象
            mock_user = Mock()
            mock_user.id = 1
            mock_user.username = "testuser"
            mock_user.display_name = "Test User"
            mock_user.created_at = datetime.now()
            mock_user.updated_at = datetime.now()
            mock_user.total_tweets = 0
            mock_user.ca_tweets = 0
            
            mock_db.refresh.return_value = None
            
            # 模拟TwitterUserResponse.model_validate
            with patch('src.services.twitter_monitor.TwitterUserResponse.model_validate') as mock_validate:
                mock_response = Mock()
                mock_validate.return_value = mock_response
                
                result = monitor_service.add_user("testuser", "Test User")
                
                assert mock_db.add.called
                assert mock_db.commit.called
            
    def test_add_existing_user(self, monitor_service):
        """测试添加已存在的用户"""
        with patch('src.services.twitter_monitor.get_db') as mock_get_db:
            mock_db = Mock()
            mock_get_db.return_value.__enter__.return_value = mock_db
            
            existing_user = Mock()
            existing_user.username = "testuser"
            mock_db.execute.return_value.scalar_one_or_none.return_value = existing_user
            
            with patch('src.services.twitter_monitor.TwitterUserResponse.model_validate') as mock_validate:
                mock_validate.return_value = Mock()
                result = monitor_service.add_user("testuser")
                
            assert not mock_db.add.called
            assert mock_validate.called
            
    def test_remove_user(self, monitor_service):
        """测试移除用户"""
        with patch('src.services.twitter_monitor.get_db') as mock_get_db:
            mock_db = Mock()
            mock_get_db.return_value.__enter__.return_value = mock_db
            
            existing_user = Mock()
            mock_db.execute.return_value.scalar_one_or_none.return_value = existing_user
            
            result = monitor_service.remove_user("testuser")
            
            assert result is True
            mock_db.delete.assert_called_with(existing_user)
            assert mock_db.commit.called
            
    def test_update_user_status(self, monitor_service):
        """测试更新用户状态"""
        with patch('src.services.twitter_monitor.get_db') as mock_get_db:
            mock_db = Mock()
            mock_get_db.return_value.__enter__.return_value = mock_db
            
            existing_user = Mock()
            existing_user.is_active = True
            mock_db.execute.return_value.scalar_one_or_none.return_value = existing_user
            
            result = monitor_service.update_user_status("testuser", False)
            
            assert result is True
            assert existing_user.is_active is False
            assert mock_db.commit.called
            
    @pytest.mark.asyncio
    async def test_check_user_tweets_new_user(self, monitor_service):
        """测试检查新用户推文"""
        with patch('src.services.twitter_monitor.get_db') as mock_get_db:
            mock_db = Mock()
            mock_get_db.return_value.__enter__.return_value = mock_db
            
            # 模拟用户没有twitter_id
            mock_user = Mock()
            mock_user.twitter_id = None
            mock_user.username = "testuser"
            
            # 模拟Twitter客户端
            monitor_service.twitter_client = Mock()
            mock_user_info = TwitterUserInfo(
                id="123456789",
                username="testuser", 
                name="Test User",
                public_metrics={},
                created_at="2020-01-01T00:00:00.000Z"
            )
            monitor_service.twitter_client.get_user_by_username = AsyncMock(return_value=mock_user_info)
            monitor_service.twitter_client.get_user_tweets = AsyncMock(return_value=[])
            
            await monitor_service.check_user_tweets(mock_db, mock_user)
            
            assert mock_user.twitter_id == "123456789"
            assert mock_user.display_name == "Test User"
            
    def test_get_statistics(self, monitor_service):
        """测试获取统计信息"""
        with patch('src.services.twitter_monitor.get_db') as mock_get_db:
            mock_db = Mock()
            mock_get_db.return_value.__enter__.return_value = mock_db
            
            # 模拟用户数据
            mock_users = [Mock(is_active=True), Mock(is_active=False)]
            mock_db.execute.return_value.scalars.return_value.all.side_effect = [
                mock_users,  # 用户查询
                []  # 推文查询
            ]
            
            result = monitor_service.get_statistics()
            
            assert result['total_users'] == 2
            assert result['active_users'] == 1


if __name__ == "__main__":
    pytest.main([__file__])