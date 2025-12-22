# src/database/models.py
"""
数据库 ORM 模型

定义市场数据的持久化结构，与币安 API 返回的 11 个字段完全对齐。
"""

from __future__ import annotations

from decimal import Decimal
from sqlalchemy import String, BigInteger, Integer, Numeric
from sqlalchemy.orm import Mapped, mapped_column

from .database import Base


class Candlestick(Base):
    """K 线数据 ORM 模型
    
    存储完整的 K 线数据，包含币安 API 返回的全部 11 个字段。
    使用复合主键 (symbol, interval, timestamp) 确保数据唯一性。
    
    Attributes:
        symbol: 交易对，如 "BTCUSDT"
        interval: 时间周期，如 "1h", "4h", "1d"
        timestamp: 开盘时间戳 (毫秒)
        open: 开盘价
        high: 最高价
        low: 最低价
        close: 收盘价
        volume: 成交量 (Base Asset)
        close_time: 收盘时间戳 (毫秒)
        quote_volume: 成交额 (Quote Asset)
        trade_count: 成交笔数
        taker_buy_base: 主动买入量 (Base Asset)
        taker_buy_quote: 主动买入额 (Quote Asset)
    """
    
    __tablename__ = "candlesticks"
    
    # === 复合主键 ===
    symbol: Mapped[str] = mapped_column(
        String(20),
        primary_key=True,
        comment="交易对"
    )
    interval: Mapped[str] = mapped_column(
        String(10),
        primary_key=True,
        comment="时间周期"
    )
    timestamp: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
        comment="开盘时间戳 (ms)"
    )
    
    # === OHLCV 核心字段 ===
    open: Mapped[Decimal] = mapped_column(
        Numeric(18, 8),
        nullable=False,
        comment="开盘价"
    )
    high: Mapped[Decimal] = mapped_column(
        Numeric(18, 8),
        nullable=False,
        comment="最高价"
    )
    low: Mapped[Decimal] = mapped_column(
        Numeric(18, 8),
        nullable=False,
        comment="最低价"
    )
    close: Mapped[Decimal] = mapped_column(
        Numeric(18, 8),
        nullable=False,
        comment="收盘价"
    )
    volume: Mapped[Decimal] = mapped_column(
        Numeric(24, 8),
        nullable=False,
        comment="成交量 (Base)"
    )
    
    # === 扩展字段 ===
    close_time: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
        comment="收盘时间戳 (ms)"
    )
    quote_volume: Mapped[Decimal] = mapped_column(
        Numeric(24, 8),
        nullable=False,
        comment="成交额 (Quote)"
    )
    trade_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="成交笔数"
    )
    taker_buy_base: Mapped[Decimal] = mapped_column(
        Numeric(24, 8),
        nullable=False,
        comment="主动买入量 (Base)"
    )
    taker_buy_quote: Mapped[Decimal] = mapped_column(
        Numeric(24, 8),
        nullable=False,
        comment="主动买入额 (Quote)"
    )
    
    def __repr__(self) -> str:
        return (
            f"<Candlestick("
            f"symbol={self.symbol!r}, "
            f"interval={self.interval!r}, "
            f"timestamp={self.timestamp}, "
            f"close={self.close}"
            f")>"
        )


class FundingRate(Base):
    """资金费率 ORM 模型
    
    存储合约市场的资金费率历史数据。
    资金费率每 8 小时结算一次。
    
    Attributes:
        symbol: 交易对，如 "BTCUSDT"
        timestamp: 结算时间戳 (毫秒)
        funding_rate: 资金费率
        mark_price: 标记价格
    """
    
    __tablename__ = "funding_rates"
    
    symbol: Mapped[str] = mapped_column(
        String(20),
        primary_key=True,
        comment="交易对"
    )
    timestamp: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
        comment="结算时间戳 (ms)"
    )
    funding_rate: Mapped[Decimal] = mapped_column(
        Numeric(18, 8),
        nullable=False,
        comment="资金费率"
    )
    mark_price: Mapped[Decimal] = mapped_column(
        Numeric(18, 8),
        nullable=False,
        comment="标记价格"
    )
    
    def __repr__(self) -> str:
        return (
            f"<FundingRate("
            f"symbol={self.symbol!r}, "
            f"timestamp={self.timestamp}, "
            f"rate={self.funding_rate}"
            f")>"
        )


class MarketSentiment(Base):
    """市场情绪 ORM 模型
    
    存储全局多空账户比数据。
    
    Attributes:
        symbol: 交易对，如 "BTCUSDT"
        timestamp: 时间戳 (毫秒)
        long_short_ratio: 多空账户比
        long_account_ratio: 多头账户占比
        short_account_ratio: 空头账户占比
    """
    
    __tablename__ = "market_sentiment"
    
    symbol: Mapped[str] = mapped_column(
        String(20),
        primary_key=True,
        comment="交易对"
    )
    timestamp: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
        comment="时间戳 (ms)"
    )
    long_short_ratio: Mapped[Decimal] = mapped_column(
        Numeric(10, 4),
        nullable=False,
        comment="多空账户比"
    )
    long_account_ratio: Mapped[Decimal] = mapped_column(
        Numeric(10, 4),
        nullable=False,
        comment="多头账户占比"
    )
    short_account_ratio: Mapped[Decimal] = mapped_column(
        Numeric(10, 4),
        nullable=False,
        comment="空头账户占比"
    )
    
    def __repr__(self) -> str:
        return (
            f"<MarketSentiment("
            f"symbol={self.symbol!r}, "
            f"timestamp={self.timestamp}, "
            f"long_short_ratio={self.long_short_ratio}"
            f")>"
        )
