# src/indicators/__init__.py
"""技术指标库

提供常用技术指标的流式计算实现，支持回测和实时计算场景。

Example:
    >>> from src.indicators import EMA, RSI, MACD, ADX, Stochastic
    >>> 
    >>> ema = EMA(20)
    >>> rsi = RSI(14)
    >>> adx = ADX(14)
    >>> 
    >>> for bar in bars:
    ...     ema_val = ema.update(bar.close)
    ...     rsi_val = rsi.update(bar.close)
    ...     adx_val = adx.update(bar.high, bar.low, bar.close)
"""

from .base import BaseIndicator, MACDResult, BollingerResult
from .ma import SMA, EMA
from .oscillator import RSI, MACD
from .volatility import ATR, BollingerBands
from .advanced import (
    ADX,
    Stochastic,
    StochasticResult,
    WilliamsR,
    CCI,
    OBV,
    Ichimoku,
    IchimokuResult,
    SentimentDisparity,
)


__all__ = [
    # 基类
    "BaseIndicator",
    "MACDResult",
    "BollingerResult",
    # 移动平均
    "SMA",
    "EMA",
    # 振荡器
    "RSI",
    "MACD",
    # 波动率
    "ATR",
    "BollingerBands",
    # 高级指标
    "ADX",
    "Stochastic",
    "StochasticResult",
    "WilliamsR",
    "CCI",
    "OBV",
    "Ichimoku",
    "IchimokuResult",
    "SentimentDisparity",
]
