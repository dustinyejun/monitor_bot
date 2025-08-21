from sqlalchemy import Column, String, Integer, Boolean, Text, ForeignKey, Index, Numeric, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import JSON
from decimal import Decimal
from .base import BaseModel


class SolanaWallet(BaseModel):
    """Solana钱包模型"""
    
    __tablename__ = "solana_wallets"
    
    # 钱包基本信息
    address = Column(
        String(44),  # Solana地址固定长度
        unique=True,
        nullable=False,
        index=True,
        comment="Solana钱包地址"
    )
    alias = Column(
        String(100),
        nullable=True,
        comment="钱包别名（用于显示）"
    )
    description = Column(
        Text,
        nullable=True,
        comment="钱包描述信息"
    )
    
    # 监控配置
    min_amount_usd = Column(
        Numeric(12, 2),
        default=Decimal("1000.00"),
        nullable=False,
        comment="最小监控交易金额（USD）"
    )
    exclude_tokens = Column(
        JSON,
        nullable=True,
        comment="排除的代币列表（JSON格式）"
    )
    
    # 钱包统计字段已移除 - 实时从 solana_transactions 表计算
    
    # 状态信息
    is_active = Column(
        Boolean,
        default=True,
        nullable=False,
        index=True,
        comment="是否启用监控"
    )
    last_signature = Column(
        String(88),  # Solana签名长度
        nullable=True,
        comment="最后检查的交易签名"
    )
    last_check_at = Column(
        String(50),  # 存储ISO时间字符串
        nullable=True,
        comment="最后检查时间"
    )
    
    # 钱包标签
    tags = Column(
        JSON,
        nullable=True,
        comment="钱包标签（如: 聪明钱、巨鲸等）"
    )
    
    # 关系
    transactions = relationship("SolanaTransaction", back_populates="wallet", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<SolanaWallet(address='{self.address[:8]}...', alias='{self.alias}')>"


class SolanaTransaction(BaseModel):
    """Solana交易记录模型"""
    
    __tablename__ = "solana_transactions"
    
    # 交易基本信息
    signature = Column(
        String(88),  # Solana交易签名长度
        unique=True,
        nullable=False,
        index=True,
        comment="交易签名"
    )
    wallet_id = Column(
        Integer,
        ForeignKey("solana_wallets.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="关联的钱包ID"
    )
    
    # 交易类型和状态
    transaction_type = Column(
        String(50),
        nullable=False,
        index=True,
        comment="交易类型：buy, sell, transfer, swap等"
    )
    status = Column(
        String(20),
        default="confirmed",
        nullable=False,
        comment="交易状态：confirmed, failed, pending"
    )
    
    # 代币信息
    token_address = Column(
        String(44),
        nullable=True,
        index=True,
        comment="代币合约地址"
    )
    token_symbol = Column(
        String(20),
        nullable=True,
        comment="代币符号"
    )
    token_name = Column(
        String(100),
        nullable=True,
        comment="代币名称"
    )
    token_decimals = Column(
        Integer,
        nullable=True,
        comment="代币精度"
    )
    
    # 交易金额
    amount = Column(
        Numeric(30, 18),  # 支持大数精度
        nullable=True,
        comment="代币数量（原始精度）"
    )
    amount_usd = Column(
        Numeric(15, 2),
        nullable=True,
        comment="交易金额（USD）"
    )
    
    # SOL费用
    fee = Column(
        Numeric(15, 9),  # SOL精度
        nullable=True,
        comment="交易手续费（SOL）"
    )
    fee_usd = Column(
        Numeric(10, 2),
        nullable=True,
        comment="手续费（USD）"
    )
    
    # 价格信息
    token_price_usd = Column(
        Numeric(15, 8),
        nullable=True,
        comment="代币价格（USD）"
    )
    sol_price_usd = Column(
        Numeric(10, 2),
        nullable=True,
        comment="SOL价格（USD）"
    )
    
    # 交易对手信息（如果适用）
    counterpart_address = Column(
        String(44),
        nullable=True,
        comment="交易对手地址"
    )
    
    # DEX信息（如果是交换）
    dex_name = Column(
        String(50),
        nullable=True,
        comment="DEX名称：Raydium, Orca, Jupiter等"
    )
    pool_address = Column(
        String(44),
        nullable=True,
        comment="流动性池地址"
    )
    
    # 区块链信息
    slot = Column(
        String(20),
        nullable=True,
        comment="区块槽位"
    )
    block_time = Column(
        DateTime(timezone=True),
        nullable=True,
        index=True,
        comment="区块时间"
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
    
    # 扩展信息
    raw_transaction = Column(
        JSON,
        nullable=True,
        comment="原始交易数据（JSON格式）"
    )
    parsed_instructions = Column(
        JSON,
        nullable=True,
        comment="解析后的指令数据（JSON格式）"
    )
    
    # 外部链接
    solscan_url = Column(
        String(500),
        nullable=True,
        comment="Solscan浏览器链接"
    )
    
    # 关系
    wallet = relationship("SolanaWallet", back_populates="transactions")
    
    def __repr__(self):
        return f"<SolanaTransaction(signature='{self.signature[:8]}...', type='{self.transaction_type}')>"


# 创建复合索引
Index('idx_solana_wallets_active_amount', SolanaWallet.is_active, SolanaWallet.min_amount_usd)
Index('idx_solana_transactions_wallet_processed', SolanaTransaction.wallet_id, SolanaTransaction.is_processed)
Index('idx_solana_transactions_type_amount', SolanaTransaction.transaction_type, SolanaTransaction.amount_usd)
Index('idx_solana_transactions_token_time', SolanaTransaction.token_address, SolanaTransaction.block_time)
Index('idx_solana_transactions_amount_time', SolanaTransaction.amount_usd, SolanaTransaction.block_time.desc())