"""
测试配置文件
配置pytest和测试环境
"""

import pytest
import asyncio
from unittest.mock import Mock
import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@pytest.fixture(scope="session")
def event_loop():
    """创建事件循环供异步测试使用"""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def mock_settings():
    """模拟设置对象"""
    settings = Mock()
    settings.TWITTER_BEARER_TOKEN = "test_bearer_token"
    settings.DATABASE_URL = "sqlite:///test.db"
    settings.WECHAT_WEBHOOK_URL = "https://test.webhook.com"
    return settings


@pytest.fixture
def mock_db_session():
    """模拟数据库会话"""
    session = Mock()
    session.add = Mock()
    session.commit = Mock()
    session.rollback = Mock()
    session.delete = Mock()
    session.refresh = Mock()
    return session