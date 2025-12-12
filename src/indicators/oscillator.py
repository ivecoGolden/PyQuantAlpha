# src/indicators/oscillator.py
"""振荡器指标模块"""

from typing import Optional
from dataclasses import dataclass

from .base import BaseIndicator, MACDResult
from .ma import EMA


class RSI(BaseIndicator):
    """相对强弱指标 (Relative Strength Index)
    
    计算公式:
        RSI = 100 - 100 / (1 + RS)
        RS = 平均涨幅 / 平均跌幅
    
    使用 Wilder 平滑法（指数移动平均）
    
    Example:
        >>> rsi = RSI(14)
        >>> for bar in bars:
        ...     result = rsi.update(bar.close)
        ...     if result and result < 30:
        ...         print("超卖区域")
    """
    
    def __init__(self, period: int = 14) -> None:
        """初始化 RSI
        
        Args:
            period: 计算周期，默认 14
        """
        super().__init__(period)
        self._prev_price: Optional[float] = None
        self._avg_gain = 0.0
        self._avg_loss = 0.0
        self._count = 0
    
    def update(self, value: float) -> Optional[float]:
        """更新 RSI 值
        
        Args:
            value: 新的价格数据（通常是收盘价）
            
        Returns:
            RSI 值 (0-100)，数据不足时返回 None
        """
        if self._prev_price is None:
            self._prev_price = value
            return None
        
        # 计算涨跌幅
        change = value - self._prev_price
        gain = max(change, 0)
        loss = abs(min(change, 0))
        
        self._count += 1
        self._prev_price = value
        
        if self._count <= self.period:
            # 初始阶段：累积平均
            self._avg_gain = (self._avg_gain * (self._count - 1) + gain) / self._count
            self._avg_loss = (self._avg_loss * (self._count - 1) + loss) / self._count
            
            if self._count < self.period:
                return None
        else:
            # Wilder 平滑
            self._avg_gain = (self._avg_gain * (self.period - 1) + gain) / self.period
            self._avg_loss = (self._avg_loss * (self.period - 1) + loss) / self.period
        
        # 计算 RSI
        if self._avg_loss == 0:
            self._result = 100.0
        else:
            rs = self._avg_gain / self._avg_loss
            self._result = 100.0 - 100.0 / (1 + rs)
        
        return self._result
    
    def reset(self) -> None:
        """重置 RSI 状态"""
        super().reset()
        self._prev_price = None
        self._avg_gain = 0.0
        self._avg_loss = 0.0
        self._count = 0


class MACD(BaseIndicator):
    """MACD 指标 (Moving Average Convergence Divergence)
    
    计算公式:
        MACD Line = EMA(fast) - EMA(slow)
        Signal Line = EMA(MACD Line, signal)
        Histogram = MACD Line - Signal Line
    
    Example:
        >>> macd = MACD(12, 26, 9)
        >>> for bar in bars:
        ...     result = macd.update(bar.close)
        ...     if result:
        ...         print(f"MACD: {result.macd_line:.2f}")
    """
    
    def __init__(
        self, 
        fast_period: int = 12, 
        slow_period: int = 26, 
        signal_period: int = 9
    ) -> None:
        """初始化 MACD
        
        Args:
            fast_period: 快线周期，默认 12
            slow_period: 慢线周期，默认 26
            signal_period: 信号线周期，默认 9
        """
        # 使用 slow_period 作为基础周期
        super().__init__(slow_period)
        
        self.fast_period = fast_period
        self.slow_period = slow_period
        self.signal_period = signal_period
        
        self._fast_ema = EMA(fast_period)
        self._slow_ema = EMA(slow_period)
        self._signal_ema = EMA(signal_period)
        
        self._macd_result: Optional[MACDResult] = None
    
    def update(self, value: float) -> Optional[MACDResult]:
        """更新 MACD 值
        
        Args:
            value: 新的价格数据
            
        Returns:
            MACDResult 对象，数据不足时返回 None
        """
        fast_val = self._fast_ema.update(value)
        slow_val = self._slow_ema.update(value)
        
        if fast_val is None or slow_val is None:
            return None
        
        macd_line = fast_val - slow_val
        signal_val = self._signal_ema.update(macd_line)
        
        if signal_val is None:
            return None
        
        histogram = macd_line - signal_val
        
        self._macd_result = MACDResult(
            macd_line=macd_line,
            signal_line=signal_val,
            histogram=histogram
        )
        self._result = macd_line  # 兼容基类 value 属性
        
        return self._macd_result
    
    @property
    def macd_value(self) -> Optional[MACDResult]:
        """获取完整 MACD 结果"""
        return self._macd_result
    
    def reset(self) -> None:
        """重置 MACD 状态"""
        super().reset()
        self._fast_ema.reset()
        self._slow_ema.reset()
        self._signal_ema.reset()
        self._macd_result = None
