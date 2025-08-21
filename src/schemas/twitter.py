from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field, validator
from decimal import Decimal


class TwitterUserBase(BaseModel):
    """推特用户基础模式"""
    username: str = Field(..., min_length=1, max_length=100, description="推特用户名")
    display_name: Optional[str] = Field(None, max_length=200, description="显示名称")
    is_active: bool = Field(True, description="是否启用监控")
    
    @validator('username')
    def validate_username(cls, v):
        """验证用户名格式"""
        if not v.replace('_', '').replace('-', '').isalnum():
            raise ValueError('用户名只能包含字母、数字、下划线和连字符')
        return v.lower()


class TwitterUserCreate(TwitterUserBase):
    """创建推特用户模式"""
    pass


class TwitterUserUpdate(BaseModel):
    """更新推特用户模式"""
    display_name: Optional[str] = Field(None, max_length=200)
    is_active: Optional[bool] = None


class TwitterUserResponse(TwitterUserBase):
    """推特用户响应模式"""
    id: int = Field(..., description="用户ID")
    twitter_id: Optional[str] = Field(None, description="推特用户ID")
    last_tweet_id: Optional[str] = Field(None, description="最后检查的推文ID")
    last_check_at: Optional[str] = Field(None, description="最后检查时间")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")
    
    # 统计信息
    total_tweets: int = Field(0, description="推文总数")
    ca_tweets: int = Field(0, description="包含CA地址的推文数")
    
    class Config:
        from_attributes = True


class TweetBase(BaseModel):
    """推文基础模式"""
    tweet_id: str = Field(..., min_length=1, max_length=50, description="推文ID")
    content: str = Field(..., min_length=1, description="推文内容")
    tweet_url: Optional[str] = Field(None, max_length=500, description="推文链接")
    ca_addresses: Optional[List[str]] = Field(default_factory=list, description="CA地址列表")
    tweet_created_at: Optional[str] = Field(None, description="推文发布时间")


class TweetResponse(TweetBase):
    """推文响应模式"""
    id: int = Field(..., description="推文ID")
    user_id: int = Field(..., description="用户ID")
    is_processed: bool = Field(False, description="是否已处理")
    is_notified: bool = Field(False, description="是否已通知")
    like_count: int = Field(0, description="点赞数")
    retweet_count: int = Field(0, description="转发数")
    reply_count: int = Field(0, description="回复数")
    created_at: datetime = Field(..., description="创建时间")
    
    # 关联用户信息
    user: Optional[TwitterUserResponse] = None
    
    class Config:
        from_attributes = True


class TwitterStatsResponse(BaseModel):
    """推特统计响应模式"""
    total_users: int = Field(..., description="总用户数")
    active_users: int = Field(..., description="活跃用户数")
    total_tweets: int = Field(..., description="总推文数")
    ca_tweets: int = Field(..., description="包含CA地址的推文数")
    today_tweets: int = Field(..., description="今日推文数")
    today_ca_tweets: int = Field(..., description="今日CA推文数")


class TwitterSearchRequest(BaseModel):
    """推特搜索请求模式"""
    username: Optional[str] = Field(None, description="用户名过滤")
    has_ca: Optional[bool] = Field(None, description="是否包含CA地址")
    keyword: Optional[str] = Field(None, description="关键词搜索")
    start_date: Optional[str] = Field(None, description="开始日期")
    end_date: Optional[str] = Field(None, description="结束日期")
    limit: int = Field(20, ge=1, le=100, description="返回数量")
    offset: int = Field(0, ge=0, description="偏移量")