# src/data/base.py
"""交易所客户端抽象基类"""

from abc import ABC, abstractmethod
from typing import List, Optional

from .models import Bar


class BaseExchangeClient(ABC):
    """交易所客户端抽象基类
    
    所有交易所客户端（Binance, OKX, Bybit 等）都应继承此类。
    
    Example:
        >>> class OKXClient(BaseExchangeClient):
        ...     def get_klines(self, symbol, interval, **kwargs):
        ...         # OKX 特定实现
        ...         pass
    """
    
    @abstractmethod
    def get_klines(
        self,
        symbol: str,
        interval: str,
        start_time: Optional[int] = None,
        end_time: Optional[int] = None,
        limit: int = 500
    ) -> List[Bar]:
        """获取 K 线数据
        
        Args:
            symbol: 交易对，如 "BTCUSDT"
            interval: 时间周期，如 "1m", "1h", "1d"
            start_time: 开始时间戳 (毫秒)，可选
            end_time: 结束时间戳 (毫秒)，可选
            limit: 返回数量
            
        Returns:
            K 线数据列表
        """
        pass
