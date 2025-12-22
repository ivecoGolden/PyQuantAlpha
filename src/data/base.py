# src/data/base.py
"""交易所客户端抽象基类"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List, Optional

from .models import Bar


class BaseExchangeClient(ABC):
    """交易所客户端抽象基类
    
    定义统一的数据获取接口，支持多交易所扩展。
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
            limit: 返回数量，默认 500
            
        Returns:
            K 线数据列表
        """
        pass
    
    @abstractmethod
    def get_historical_klines(
        self,
        symbol: str,
        interval: str,
        days: int
    ) -> List[Bar]:
        """批量获取历史 K 线数据
        
        Args:
            symbol: 交易对
            interval: 时间周期
            days: 获取最近 N 天的数据
            
        Returns:
            K 线数据列表（按时间正序）
        """
        pass
