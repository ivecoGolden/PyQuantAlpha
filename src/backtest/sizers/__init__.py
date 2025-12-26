# src/backtest/sizers/__init__.py
"""
Sizer 模块 - 资金管理体系

将 "交易什么" (Strategy) 与 "交易多少" (Sizer) 解耦。

可用的 Sizer 类型：
- FixedSize: 固定数量
- PercentSize: 按可用资金百分比
- AllIn: 全仓
- RiskSize: 基于 ATR 的风险仓位

Example:
    >>> from src.backtest.sizers import PercentSize, SizerParams
    >>> sizer = PercentSize(SizerParams(percent=30))
    >>> sizer.set_broker(broker)
    >>> size = sizer.get_size(data, isbuy=True)
"""

from src.backtest.sizers.base import BaseSizer, SizerParams
from src.backtest.sizers.fixed import FixedSize
from src.backtest.sizers.percent import PercentSize, AllIn
from src.backtest.sizers.risk import RiskSize

__all__ = [
    "BaseSizer",
    "SizerParams",
    "FixedSize",
    "PercentSize",
    "AllIn",
    "RiskSize",
]
