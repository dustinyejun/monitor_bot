from sqlalchemy import Column, String, Integer, Boolean, Text, ForeignKey, Index
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import JSON
from .base import BaseModel


class TwitterUser(BaseModel):
    """推特用户模型"""
    
    __tablename__ = "twitter_users"
    
    # 基本信息
    username = Column(
        String(100), 
        unique=True, 
        nullable=False, 
        index=True,
        comment="推特用户名（@后面的部分）"
    )
    display_name = Column(
        String(200),
        nullable=True,
        comment="推特显示名称"
    )
    twitter_id = Column(
        String(50),
        unique=True,
        nullable=True,
        index=True,
        comment="推特用户ID"
    )
    
    
    # 监控配置
    is_active = Column(
        Boolean,
        default=True,
        nullable=False,
        index=True,
        comment="是否启用监控"
    )
    
    # 状态信息
    last_tweet_id = Column(
        String(50),
        nullable=True,
        comment="最后检查的推文ID"
    )
    last_check_at = Column(
        String(50),  # 存储ISO时间字符串
        nullable=True,
        comment="最后检查时间"
    )
    
    # 关系
    tweets = relationship("Tweet", back_populates="user", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<TwitterUser(username='{self.username}', display_name='{self.display_name}')>"


class Tweet(BaseModel):
    """推文记录模型"""
    
    __tablename__ = "tweets"
    
    # 推文基本信息
    tweet_id = Column(
        String(50),
        unique=True,
        nullable=False,
        index=True,
        comment="推特推文ID"
    )
    user_id = Column(
        Integer,
        ForeignKey("twitter_users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="关联的推特用户ID"
    )
    
    # 推文内容
    content = Column(
        Text,
        nullable=False,
        comment="推文完整内容"
    )
    tweet_url = Column(
        String(500),
        nullable=True,
        comment="推文链接"
    )
    
    # 分析结果
    ca_addresses = Column(
        JSON,
        nullable=True,
        comment="检测到的CA地址列表（JSON格式）"
    )
    
    # 处理状态
    is_processed = Column(
        Boolean,
        default=False,
        nullable=False,
        index=True,
        comment="是否已处理"
    )
    is_notified = Column(
        Boolean,
        default=False,
        nullable=False,
        index=True,
        comment="是否已通知"
    )
    
    # 推文统计
    like_count = Column(
        Integer,
        default=0,
        nullable=False,
        comment="点赞数"
    )
    retweet_count = Column(
        Integer,
        default=0,
        nullable=False,
        comment="转发数"
    )
    reply_count = Column(
        Integer,
        default=0,
        nullable=False,
        comment="回复数"
    )
    
    # 推文时间
    tweet_created_at = Column(
        String(50),  # 存储ISO时间字符串
        nullable=True,
        comment="推文发布时间"
    )
    
    # 关系
    user = relationship("TwitterUser", back_populates="tweets")
    
    def __repr__(self):
        return f"<Tweet(tweet_id='{self.tweet_id}', content='{self.content[:50]}...')>"


# 创建索引
Index('idx_twitter_users_active', TwitterUser.is_active)
Index('idx_tweets_user_processed', Tweet.user_id, Tweet.is_processed)
Index('idx_tweets_ca_addresses', Tweet.ca_addresses)  # GIN索引，用于JSON搜索