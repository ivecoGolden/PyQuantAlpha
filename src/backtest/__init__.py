# src/backtest/__init__.py
"""
回测引擎模块

提供事件驱动的策略回测框架，支持：
- 多空双向交易模拟
- 手续费、滑点模拟
- 净值曲线与绩效分析
- SSE 实时进度推送
- 策略回调钩子 (notify_order/notify_trade)

核心组件：
- BacktestEngine: 回测引擎核心
- BacktestAnalyzer: 绩效分析器
- BacktestManager: 异步任务管理 (SSE)
- BacktestLogger: 日志与可视化数据收集
"""

from .models import (
    OrderSide,
    OrderStatus,
    OrderType,
    Order,
    Trade,
    Position,
    BacktestConfig,
    BacktestResult,
)
from .engine import BacktestEngine
from .analyzer import BacktestAnalyzer

__all__ = [
    "OrderSide",
    "OrderStatus",
    "OrderType",
    "Order",
    "Trade",
    "Position",
    "BacktestConfig",
    "BacktestResult",
    "BacktestEngine",
    "BacktestAnalyzer",
]
