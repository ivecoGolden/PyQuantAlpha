# src/indicators/volatility.py
"""波动率指标模块"""

from typing import Optional

from .base import BaseIndicator, BollingerResult
from .ma import SMA


class ATR(BaseIndicator):
    """平均真实波幅 (Average True Range)
    
    True Range = max(high - low, |high - prev_close|, |low - prev_close|)
    ATR = EMA(True Range, period) 或 SMA
    
    本实现使用 Wilder 平滑法
    
    Example:
        >>> atr = ATR(14)
        >>> for bar in bars:
        ...     result = atr.update(bar.high, bar.low, bar.close)
        ...     if result:
        ...         stop_loss = bar.close - 2 * result
    """
    
    def __init__(self, period: int = 14) -> None:
        """初始化 ATR
        
        Args:
            period: 计算周期，默认 14
        """
        super().__init__(period)
        self._prev_close: Optional[float] = None
        self._tr_values: list[float] = []
        self._count = 0
    
    def update(
        self, 
        high: float, 
        low: float, 
        close: float
    ) -> Optional[float]:
        """更新 ATR 值
        
        Args:
            high: 最高价
            low: 最低价
            close: 收盘价
            
        Returns:
            ATR 值，数据不足时返回 None
        """
        # 计算 True Range
        if self._prev_close is None:
            tr = high - low
        else:
            tr = max(
                high - low,
                abs(high - self._prev_close),
                abs(low - self._prev_close)
            )
        
        self._prev_close = close
        self._count += 1
        
        if self._count <= self.period:
            # 初始阶段：累积
            self._tr_values.append(tr)
            
            if self._count == self.period:
                # 第一个 ATR = 简单平均
                self._result = sum(self._tr_values) / self.period
                return self._result
            return None
        else:
            # Wilder 平滑
            self._result = (self._result * (self.period - 1) + tr) / self.period
            return self._result
    
    def reset(self) -> None:
        """重置 ATR 状态"""
        super().reset()
        self._prev_close = None
        self._tr_values.clear()
        self._count = 0


class BollingerBands(BaseIndicator):
    """布林带 (Bollinger Bands)
    
    计算公式:
        Middle Band = SMA(price, period)
        Upper Band = Middle Band + std_dev * standard_deviation
        Lower Band = Middle Band - std_dev * standard_deviation
    
    Example:
        >>> bb = BollingerBands(20, 2)
        >>> for bar in bars:
        ...     result = bb.update(bar.close)
        ...     if result and bar.close < result.lower:
        ...         print("价格触及下轨")
    """
    
    def __init__(self, period: int = 20, std_dev: float = 2.0) -> None:
        """初始化布林带
        
        Args:
            period: 计算周期，默认 20
            std_dev: 标准差倍数，默认 2.0
        """
        super().__init__(period)
        self.std_dev = std_dev
        self._bb_result: Optional[BollingerResult] = None
    
    def update(self, value: float) -> Optional[BollingerResult]:
        """更新布林带值
        
        Args:
            value: 新的价格数据
            
        Returns:
            BollingerResult 对象，数据不足时返回 None
        """
        self._values.append(value)
        
        if len(self._values) > self.period:
            self._values.pop(0)
        
        if len(self._values) < self.period:
            return None
        
        # 计算 SMA（中轨）
        middle = sum(self._values) / self.period
        
        # 计算标准差
        variance = sum((x - middle) ** 2 for x in self._values) / self.period
        std = variance ** 0.5
        
        # 计算上下轨
        upper = middle + self.std_dev * std
        lower = middle - self.std_dev * std
        
        self._bb_result = BollingerResult(
            upper=upper,
            middle=middle,
            lower=lower
        )
        self._result = middle  # 兼容基类 value 属性
        
        return self._bb_result
    
    @property
    def bands(self) -> Optional[BollingerResult]:
        """获取完整布林带结果"""
        return self._bb_result
    
    def reset(self) -> None:
        """重置布林带状态"""
        super().reset()
        self._bb_result = None
