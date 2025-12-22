# src/indicators/advanced.py
"""高级技术指标

包含趋势型、动量型和成交量型的高阶指标实现。
"""

from __future__ import annotations
from typing import Optional, List
from dataclasses import dataclass

from .base import BaseIndicator
from .ma import EMA


@dataclass
class IchimokuResult:
    """一目均衡表计算结果"""
    tenkan: float      # 转换线 (9)
    kijun: float       # 基准线 (26)
    senkou_a: float    # 先行带 A
    senkou_b: float    # 先行带 B
    chikou: float      # 延迟线


@dataclass
class StochasticResult:
    """随机指标计算结果"""
    k: float  # %K
    d: float  # %D


class ADX(BaseIndicator):
    """平均趋向指标 (Average Directional Index)
    
    用于衡量趋势的强度，不区分方向。
    ADX > 25 表示强趋势，ADX < 20 表示弱趋势或震荡。
    
    Example:
        >>> adx = ADX(14)
        >>> for bar in bars:
        ...     result = adx.update(bar.high, bar.low, bar.close)
        ...     if result:
        ...         print(f"ADX: {result:.2f}")
    """
    
    def __init__(self, period: int = 14) -> None:
        super().__init__(period)
        self._prev_high: Optional[float] = None
        self._prev_low: Optional[float] = None
        self._prev_close: Optional[float] = None
        self._tr_values: List[float] = []
        self._plus_dm_values: List[float] = []
        self._minus_dm_values: List[float] = []
        self._dx_values: List[float] = []
    
    def update(self, high: float, low: float, close: float) -> Optional[float]:
        """更新 ADX 值
        
        Args:
            high: 最高价
            low: 最低价
            close: 收盘价
            
        Returns:
            ADX 值，数据不足时返回 None
        """
        if self._prev_close is None:
            self._prev_high = high
            self._prev_low = low
            self._prev_close = close
            return None
        
        # 计算 True Range
        tr = max(
            high - low,
            abs(high - self._prev_close),
            abs(low - self._prev_close)
        )
        
        # 计算 +DM 和 -DM
        up_move = high - self._prev_high
        down_move = self._prev_low - low
        
        plus_dm = up_move if up_move > down_move and up_move > 0 else 0
        minus_dm = down_move if down_move > up_move and down_move > 0 else 0
        
        self._tr_values.append(tr)
        self._plus_dm_values.append(plus_dm)
        self._minus_dm_values.append(minus_dm)
        
        # 保存当前值
        self._prev_high = high
        self._prev_low = low
        self._prev_close = close
        
        # 需要 period 个数据
        if len(self._tr_values) < self.period:
            return None
        
        # 计算平滑 TR, +DI, -DI
        atr = sum(self._tr_values[-self.period:]) / self.period
        plus_di = 100 * sum(self._plus_dm_values[-self.period:]) / atr if atr > 0 else 0
        minus_di = 100 * sum(self._minus_dm_values[-self.period:]) / atr if atr > 0 else 0
        
        # 计算 DX
        di_sum = plus_di + minus_di
        dx = 100 * abs(plus_di - minus_di) / di_sum if di_sum > 0 else 0
        self._dx_values.append(dx)
        
        # 需要 period * 2 个 DX 值来计算 ADX
        if len(self._dx_values) < self.period:
            return None
        
        # ADX 是 DX 的平均
        self._result = sum(self._dx_values[-self.period:]) / self.period
        return self._result


class Stochastic(BaseIndicator):
    """随机指标 (Stochastic Oscillator)
    
    用于判断超买超卖状态。
    %K > 80 超买，%K < 20 超卖。
    
    Example:
        >>> stoch = Stochastic(14, 3)
        >>> for bar in bars:
        ...     result = stoch.update(bar.high, bar.low, bar.close)
        ...     if result:
        ...         print(f"K: {result.k:.2f}, D: {result.d:.2f}")
    """
    
    def __init__(self, k_period: int = 14, d_period: int = 3) -> None:
        super().__init__(k_period)
        self.d_period = d_period
        self._highs: List[float] = []
        self._lows: List[float] = []
        self._k_values: List[float] = []
    
    def update(self, high: float, low: float, close: float) -> Optional[StochasticResult]:
        """更新随机指标
        
        Args:
            high: 最高价
            low: 最低价
            close: 收盘价
            
        Returns:
            StochasticResult，数据不足时返回 None
        """
        self._highs.append(high)
        self._lows.append(low)
        
        if len(self._highs) < self.period:
            return None
        
        # 计算 %K
        highest = max(self._highs[-self.period:])
        lowest = min(self._lows[-self.period:])
        
        if highest == lowest:
            k = 50.0
        else:
            k = 100 * (close - lowest) / (highest - lowest)
        
        self._k_values.append(k)
        
        if len(self._k_values) < self.d_period:
            return None
        
        # 计算 %D (K 的移动平均)
        d = sum(self._k_values[-self.d_period:]) / self.d_period
        
        return StochasticResult(k=k, d=d)


class WilliamsR(BaseIndicator):
    """威廉指标 (Williams %R)
    
    与随机指标类似，但取值范围为 -100 到 0。
    %R < -80 超卖，%R > -20 超买。
    
    Example:
        >>> wr = WilliamsR(14)
        >>> for bar in bars:
        ...     result = wr.update(bar.high, bar.low, bar.close)
    """
    
    def __init__(self, period: int = 14) -> None:
        super().__init__(period)
        self._highs: List[float] = []
        self._lows: List[float] = []
    
    def update(self, high: float, low: float, close: float) -> Optional[float]:
        """更新威廉指标"""
        self._highs.append(high)
        self._lows.append(low)
        
        if len(self._highs) < self.period:
            return None
        
        highest = max(self._highs[-self.period:])
        lowest = min(self._lows[-self.period:])
        
        if highest == lowest:
            self._result = -50.0
        else:
            self._result = -100 * (highest - close) / (highest - lowest)
        
        return self._result


class CCI(BaseIndicator):
    """顺势指标 (Commodity Channel Index)
    
    用于判断价格偏离均值的程度。
    CCI > 100 超买，CCI < -100 超卖。
    
    Example:
        >>> cci = CCI(20)
        >>> for bar in bars:
        ...     result = cci.update(bar.high, bar.low, bar.close)
    """
    
    def __init__(self, period: int = 20) -> None:
        super().__init__(period)
        self._tp_values: List[float] = []
    
    def update(self, high: float, low: float, close: float) -> Optional[float]:
        """更新 CCI"""
        # 典型价格 (Typical Price)
        tp = (high + low + close) / 3
        self._tp_values.append(tp)
        
        if len(self._tp_values) < self.period:
            return None
        
        recent = self._tp_values[-self.period:]
        tp_mean = sum(recent) / self.period
        
        # 平均绝对偏差
        mad = sum(abs(x - tp_mean) for x in recent) / self.period
        
        if mad == 0:
            self._result = 0.0
        else:
            self._result = (tp - tp_mean) / (0.015 * mad)
        
        return self._result


class OBV(BaseIndicator):
    """能量潮指标 (On-Balance Volume)
    
    基于成交量的累积指标，用于判断资金流向。
    
    Example:
        >>> obv = OBV()
        >>> for bar in bars:
        ...     result = obv.update(bar.close, bar.volume)
    """
    
    def __init__(self) -> None:
        super().__init__(1)  # period 不适用
        self._prev_close: Optional[float] = None
        self._obv: float = 0.0
    
    def update(self, close: float, volume: float) -> float:
        """更新 OBV
        
        Args:
            close: 收盘价
            volume: 成交量
            
        Returns:
            当前 OBV 值
        """
        if self._prev_close is None:
            self._prev_close = close
            self._result = 0.0
            return self._result
        
        if close > self._prev_close:
            self._obv += volume
        elif close < self._prev_close:
            self._obv -= volume
        # close == prev_close 时 OBV 不变
        
        self._prev_close = close
        self._result = self._obv
        return self._result


class Ichimoku:
    """一目均衡表 (Ichimoku Cloud)
    
    日本技术分析指标，包含五条线。
    
    注意：Ichimoku 不继承 BaseIndicator，因为它返回多个值。
    
    Example:
        >>> ichi = Ichimoku()
        >>> for bar in bars:
        ...     result = ichi.update(bar.high, bar.low, bar.close)
        ...     if result:
        ...         print(f"Tenkan: {result.tenkan:.2f}")
    """
    
    def __init__(
        self,
        tenkan_period: int = 9,
        kijun_period: int = 26,
        senkou_b_period: int = 52
    ) -> None:
        self.tenkan_period = tenkan_period
        self.kijun_period = kijun_period
        self.senkou_b_period = senkou_b_period
        
        self._highs: List[float] = []
        self._lows: List[float] = []
        self._closes: List[float] = []
    
    def _midpoint(self, period: int) -> Optional[float]:
        """计算周期内的中点值"""
        if len(self._highs) < period:
            return None
        highest = max(self._highs[-period:])
        lowest = min(self._lows[-period:])
        return (highest + lowest) / 2
    
    def update(self, high: float, low: float, close: float) -> Optional[IchimokuResult]:
        """更新一目均衡表
        
        Args:
            high: 最高价
            low: 最低价
            close: 收盘价
            
        Returns:
            IchimokuResult，数据不足时返回 None
        """
        self._highs.append(high)
        self._lows.append(low)
        self._closes.append(close)
        
        if len(self._highs) < self.senkou_b_period:
            return None
        
        tenkan = self._midpoint(self.tenkan_period)
        kijun = self._midpoint(self.kijun_period)
        
        if tenkan is None or kijun is None:
            return None
        
        senkou_a = (tenkan + kijun) / 2
        senkou_b = self._midpoint(self.senkou_b_period)
        
        if senkou_b is None:
            return None
        
        # 延迟线是当前收盘价 (实际应该绘制在 26 周期前)
        chikou = close
        
        return IchimokuResult(
            tenkan=tenkan,
            kijun=kijun,
            senkou_a=senkou_a,
            senkou_b=senkou_b,
            chikou=chikou
        )
    
    def reset(self) -> None:
        """重置状态"""
        self._highs.clear()
        self._lows.clear()
        self._closes.clear()


# ============ 自定义情感指标 ============

class SentimentDisparity(BaseIndicator):
    """情绪背离指标 (Sentiment Disparity)
    
    衡量价格走势与账户多空比走势之间的分歧。
    当价格上涨但多空比下降时（散户下车/大户接盘），可能预示趋势持续。
    当价格下跌但多空比上升时（散户抄底/大户出货），可能预示进一步下跌。
    
    公式: (Price_Change% - Ratio_Change%) * 100
    
    Example:
        >>> sd = SentimentDisparity(period=1)
        >>> for bar, sentiment in zip(bars, sentiments):
        ...     val = sd.update(bar.close, sentiment.long_short_ratio)
    """
    
    def __init__(self, period: int = 1) -> None:
        super().__init__(period)
        self._prev_price: Optional[float] = None
        self._prev_ratio: Optional[float] = None
    
    def update(self, price: float, ratio: float) -> Optional[float]:
        """更新背离指标
        
        Args:
            price: 当前价格
            ratio: 当前多空比
            
        Returns:
            分歧值 (正值表示多头背离，负值表示空头背离)
        """
        if self._prev_price is None or self._prev_ratio is None:
            self._prev_price = price
            self._prev_ratio = ratio
            return None
            
        price_change = (price - self._prev_price) / self._prev_price if self._prev_price != 0 else 0
        ratio_change = (ratio - self._prev_ratio) / self._prev_ratio if self._prev_ratio != 0 else 0
        
        # 背离值：价格变化率 - 多空比变化率
        self._result = (price_change - ratio_change) * 100
        
        self._prev_price = price
        self._prev_ratio = ratio
        return self._result
