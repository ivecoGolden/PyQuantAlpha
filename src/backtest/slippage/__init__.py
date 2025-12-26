# src/backtest/slippage/__init__.py
"""
滑点模型模块

提供多种滑点计算模型，用于提升回测的仿真精度。

可用的滑点模型：
- FixedSlippage: 固定金额滑点
- PercentSlippage: 百分比滑点
- VolumeSlippage: 成交量滑点（冲击成本）

Example:
    >>> from src.backtest.slippage import PercentSlippage, SlippageParams
    >>> slippage = PercentSlippage(SlippageParams(percent=0.001))
    >>> executed_price = slippage.calculate(100.0, 1.0, is_buy=True)
"""

from src.backtest.slippage.base import BaseSlippage, SlippageParams
from src.backtest.slippage.fixed import FixedSlippage
from src.backtest.slippage.percent import PercentSlippage, VolumeSlippage

__all__ = [
    "BaseSlippage",
    "SlippageParams",
    "FixedSlippage",
    "PercentSlippage",
    "VolumeSlippage",
]
