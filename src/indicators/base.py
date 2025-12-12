# src/indicators/base.py
"""指标基类模块"""

from abc import ABC, abstractmethod
from typing import Optional
from dataclasses import dataclass


@dataclass
class MACDResult:
    """MACD 计算结果"""
    macd_line: float
    signal_line: float
    histogram: float


@dataclass
class BollingerResult:
    """布林带计算结果"""
    upper: float
    middle: float
    lower: float


class BaseIndicator(ABC):
    """指标基类 - 流式计算接口
    
    所有技术指标必须继承此类并实现 update() 方法。
    支持逐条数据更新，适用于实时计算和回测场景。
    
    Example:
        >>> ema = EMA(20)
        >>> for bar in bars:
        ...     result = ema.update(bar.close)
        ...     if result is not None:
        ...         print(f"EMA: {result:.2f}")
    """
    
    def __init__(self, period: int) -> None:
        """初始化指标
        
        Args:
            period: 计算周期
        """
        if period < 1:
            raise ValueError(f"周期必须 >= 1, 当前值: {period}")
        
        self.period = period
        self._values: list[float] = []
        self._result: Optional[float] = None
    
    @abstractmethod
    def update(self, value: float) -> Optional[float]:
        """更新指标值
        
        Args:
            value: 新的价格数据
            
        Returns:
            计算结果，数据不足时返回 None
        """
        pass
    
    @property
    def value(self) -> Optional[float]:
        """获取当前指标值"""
        return self._result
    
    @property
    def ready(self) -> bool:
        """指标是否已准备好（有足够数据）"""
        return self._result is not None
    
    def reset(self) -> None:
        """重置指标状态"""
        self._values.clear()
        self._result = None
    
    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(period={self.period}, value={self._result})"
