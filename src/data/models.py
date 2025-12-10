"""数据模型定义"""

from dataclasses import dataclass


@dataclass
class Bar:
    """K 线数据结构
    
    Attributes:
        timestamp: 开盘时间戳 (毫秒)
        open: 开盘价
        high: 最高价
        low: 最低价
        close: 收盘价
        volume: 成交量
    """
    timestamp: int
    open: float
    high: float
    low: float
    close: float
    volume: float
