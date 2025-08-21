from datetime import datetime
from sqlalchemy import Column, Integer, DateTime, func
from sqlalchemy.ext.declarative import declarative_base, declared_attr
from typing import Any


class CustomBase:
    """自定义基础模型类"""
    
    @declared_attr
    def __tablename__(cls) -> str:
        """自动生成表名（类名转换为小写加下划线）"""
        import re
        return re.sub('([a-z0-9])([A-Z])', r'\1_\2', cls.__name__).lower()
    
    def to_dict(self) -> dict:
        """将模型实例转换为字典"""
        return {
            column.name: getattr(self, column.name)
            for column in self.__table__.columns
        }
    
    def __repr__(self) -> str:
        """字符串表示"""
        return f"<{self.__class__.__name__}({self.to_dict()})>"


# 创建基础模型类
Base = declarative_base(cls=CustomBase)


class TimestampMixin:
    """时间戳混入类"""
    
    created_at = Column(
        DateTime(timezone=True), 
        server_default=func.now(),
        nullable=False,
        comment="创建时间"
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
        comment="更新时间"
    )


class BaseModel(Base, TimestampMixin):
    """基础模型类，包含主键和时间戳"""
    
    __abstract__ = True
    
    id = Column(
        Integer,
        primary_key=True,
        autoincrement=True,
        comment="主键ID"
    )