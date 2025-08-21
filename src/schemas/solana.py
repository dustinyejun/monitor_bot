from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, validator
from decimal import Decimal
import re


class SolanaWalletBase(BaseModel):
    """Solana钱包基础模式"""
    address: str = Field(..., min_length=32, max_length=44, description="钱包地址")
    alias: Optional[str] = Field(None, max_length=100, description="钱包别名")
    description: Optional[str] = Field(None, description="钱包描述")
    min_amount_usd: Decimal = Field(Decimal("1000.00"), ge=0, description="最小监控金额")
    exclude_tokens: Optional[List[str]] = Field(default_factory=list, description="排除代币列表")
    is_active: bool = Field(True, description="是否启用监控")
    tags: Optional[List[str]] = Field(default_factory=list, description="钱包标签")
    
    @validator('address')
    def validate_address(cls, v):
        """验证Solana地址格式"""
        if not re.match(r'^[1-9A-HJ-NP-Za-km-z]{32,44}$', v):
            raise ValueError('无效的Solana地址格式')
        return v
    
    @validator('exclude_tokens', 'tags', pre=True)
    def validate_lists(cls, v):
        """验证列表字段"""
        if v is None:
            return []
        if isinstance(v, str):
            return [item.strip() for item in v.split(',') if item.strip()]
        return v


class SolanaWalletCreate(SolanaWalletBase):
    """创建Solana钱包模式"""
    pass


class SolanaWalletUpdate(BaseModel):
    """更新Solana钱包模式"""
    alias: Optional[str] = Field(None, max_length=100)
    description: Optional[str] = None
    min_amount_usd: Optional[Decimal] = Field(None, ge=0)
    exclude_tokens: Optional[List[str]] = None
    is_active: Optional[bool] = None
    tags: Optional[List[str]] = None


class SolanaWalletResponse(SolanaWalletBase):
    """Solana钱包响应模式"""
    id: int = Field(..., description="钱包ID")
    last_signature: Optional[str] = Field(None, description="最后交易签名")
    last_check_at: Optional[str] = Field(None, description="最后检查时间")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")
    
    class Config:
        from_attributes = True


class SolanaTransactionBase(BaseModel):
    """Solana交易基础模式"""
    signature: str = Field(..., min_length=87, max_length=88, description="交易签名")
    transaction_type: str = Field(..., max_length=50, description="交易类型")
    status: str = Field("confirmed", description="交易状态")
    token_address: Optional[str] = Field(None, description="代币地址")
    token_symbol: Optional[str] = Field(None, max_length=20, description="代币符号")
    token_name: Optional[str] = Field(None, max_length=100, description="代币名称")
    amount: Optional[Decimal] = Field(None, description="代币数量")
    amount_usd: Optional[Decimal] = Field(None, description="USD价值")
    
    @validator('signature')
    def validate_signature(cls, v):
        """验证交易签名格式"""
        if not re.match(r'^[1-9A-HJ-NP-Za-km-z]{87,88}$', v):
            raise ValueError('无效的Solana交易签名格式')
        return v


class SolanaTransactionResponse(SolanaTransactionBase):
    """Solana交易响应模式"""
    id: int = Field(..., description="交易ID")
    wallet_id: int = Field(..., description="钱包ID")
    token_decimals: Optional[int] = Field(None, description="代币精度")
    fee: Optional[Decimal] = Field(None, description="手续费")
    fee_usd: Optional[Decimal] = Field(None, description="手续费USD")
    token_price_usd: Optional[Decimal] = Field(None, description="代币价格")
    sol_price_usd: Optional[Decimal] = Field(None, description="SOL价格")
    counterpart_address: Optional[str] = Field(None, description="交易对手地址")
    dex_name: Optional[str] = Field(None, description="DEX名称")
    pool_address: Optional[str] = Field(None, description="流动性池地址")
    slot: Optional[str] = Field(None, description="区块槽位")
    block_time: Optional[datetime] = Field(None, description="区块时间")
    is_processed: bool = Field(False, description="是否已处理")
    is_notified: bool = Field(False, description="是否已通知")
    solscan_url: Optional[str] = Field(None, description="浏览器链接")
    created_at: datetime = Field(..., description="创建时间")
    
    # 关联钱包信息
    wallet: Optional[SolanaWalletResponse] = None
    
    class Config:
        from_attributes = True


class SolanaStatsResponse(BaseModel):
    """Solana统计响应模式"""
    total_wallets: int = Field(..., description="总钱包数")
    active_wallets: int = Field(..., description="活跃钱包数")
    total_transactions: int = Field(..., description="总交易数")
    total_volume_usd: Decimal = Field(..., description="总交易额")
    today_transactions: int = Field(..., description="今日交易数")
    today_volume_usd: Decimal = Field(..., description="今日交易额")
    
    # 按类型统计
    transaction_types: Dict[str, int] = Field(default_factory=dict, description="交易类型统计")
    top_tokens: List[Dict[str, Any]] = Field(default_factory=list, description="热门代币")


class SolanaSearchRequest(BaseModel):
    """Solana搜索请求模式"""
    wallet_address: Optional[str] = Field(None, description="钱包地址过滤")
    transaction_type: Optional[str] = Field(None, description="交易类型过滤")
    token_address: Optional[str] = Field(None, description="代币地址过滤")
    token_symbol: Optional[str] = Field(None, description="代币符号过滤")
    min_amount_usd: Optional[Decimal] = Field(None, ge=0, description="最小金额")
    max_amount_usd: Optional[Decimal] = Field(None, ge=0, description="最大金额")
    start_date: Optional[str] = Field(None, description="开始日期")
    end_date: Optional[str] = Field(None, description="结束日期")
    limit: int = Field(20, ge=1, le=100, description="返回数量")
    offset: int = Field(0, ge=0, description="偏移量")
    
    @validator('max_amount_usd')
    def validate_amount_range(cls, v, values):
        """验证金额范围"""
        if v is not None and 'min_amount_usd' in values and values['min_amount_usd'] is not None:
            if v < values['min_amount_usd']:
                raise ValueError('最大金额不能小于最小金额')
        return v


class TokenInfoResponse(BaseModel):
    """代币信息响应模式"""
    address: str = Field(..., description="代币地址")
    symbol: str = Field(..., description="代币符号")
    name: str = Field(..., description="代币名称")
    decimals: int = Field(..., description="代币精度")
    price_usd: Optional[Decimal] = Field(None, description="USD价格")
    market_cap: Optional[Decimal] = Field(None, description="市值")
    volume_24h: Optional[Decimal] = Field(None, description="24h交易量")
    logo_uri: Optional[str] = Field(None, description="代币图标")


class NotificationRequest(BaseModel):
    """通知请求模式"""
    type: str = Field(..., description="通知类型: twitter, solana")
    title: str = Field(..., description="通知标题")
    content: str = Field(..., description="通知内容")
    data: Optional[Dict[str, Any]] = Field(default_factory=dict, description="扩展数据")
    urgent: bool = Field(False, description="是否紧急")