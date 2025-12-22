# src/data/models.py
"""
数据层数据模型

定义 K 线等市场数据的内存表示。
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Bar:
    """K 线数据结构
    
    Phase 3 升级版本，包含币安 API 返回的全部 11 个字段，
    支持更丰富的市场分析维度。
    
    Attributes:
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
        
    Example:
        >>> bar = Bar(
        ...     timestamp=1699000000000,
        ...     open=35000.0,
        ...     high=35500.0,
        ...     low=34800.0,
        ...     close=35200.0,
        ...     volume=1234.56
        ... )
        >>> bar.close
        35200.0
    """
    
    # === 核心 OHLCV 字段 ===
    timestamp: int
    open: float
    high: float
    low: float
    close: float
    volume: float
    
    # === Phase 3 新增扩展字段 ===
    close_time: int = 0
    quote_volume: float = 0.0
    trade_count: int = 0
    taker_buy_base: float = 0.0
    taker_buy_quote: float = 0.0
    
    def to_dict(self) -> dict:
        """转换为字典格式
        
        Returns:
            包含所有字段的字典
        """
        return {
            "timestamp": self.timestamp,
            "open": self.open,
            "high": self.high,
            "low": self.low,
            "close": self.close,
            "volume": self.volume,
            "close_time": self.close_time,
            "quote_volume": self.quote_volume,
            "trade_count": self.trade_count,
            "taker_buy_base": self.taker_buy_base,
            "taker_buy_quote": self.taker_buy_quote,
        }
    
    def to_basic_dict(self) -> dict:
        """转换为基础 OHLCV 字典格式（兼容旧 API）
        
        Returns:
            仅包含核心字段的字典
        """
        return {
            "timestamp": self.timestamp,
            "open": self.open,
            "high": self.high,
            "low": self.low,
            "close": self.close,
            "volume": self.volume,
        }
