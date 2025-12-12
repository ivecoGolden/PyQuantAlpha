# src/indicators/ma.py
"""移动平均指标模块"""

from typing import Optional

from .base import BaseIndicator


class SMA(BaseIndicator):
    """简单移动平均 (Simple Moving Average)
    
    计算公式: SMA = sum(prices) / period
    
    Example:
        >>> sma = SMA(5)
        >>> prices = [10, 11, 12, 13, 14]
        >>> for p in prices:
        ...     result = sma.update(p)
        >>> print(result)  # 12.0
    """
    
    def update(self, value: float) -> Optional[float]:
        """更新 SMA 值
        
        Args:
            value: 新的价格数据
            
        Returns:
            SMA 值，数据不足时返回 None
        """
        self._values.append(value)
        
        # 保持窗口大小
        if len(self._values) > self.period:
            self._values.pop(0)
        
        # 数据足够时计算
        if len(self._values) == self.period:
            self._result = sum(self._values) / self.period
            return self._result
        
        return None


class EMA(BaseIndicator):
    """指数移动平均 (Exponential Moving Average)
    
    计算公式: 
        EMA = price * alpha + EMA_prev * (1 - alpha)
        alpha = 2 / (period + 1)
    
    Example:
        >>> ema = EMA(20)
        >>> for bar in bars:
        ...     result = ema.update(bar.close)
    """
    
    def __init__(self, period: int) -> None:
        """初始化 EMA
        
        Args:
            period: 计算周期
        """
        super().__init__(period)
        self._alpha = 2.0 / (period + 1)
        self._count = 0
    
    def update(self, value: float) -> Optional[float]:
        """更新 EMA 值
        
        Args:
            value: 新的价格数据
            
        Returns:
            EMA 值，数据不足时返回 None
        """
        self._count += 1
        
        if self._result is None:
            # 首个值直接作为 EMA
            self._result = value
        else:
            # EMA 递推公式
            self._result = value * self._alpha + self._result * (1 - self._alpha)
        
        # 周期内数据不足时不返回
        if self._count < self.period:
            return None
        
        return self._result
    
    def reset(self) -> None:
        """重置 EMA 状态"""
        super().reset()
        self._count = 0
