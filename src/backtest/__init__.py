# src/backtest/__init__.py
"""
回测引擎模块

提供事件驱动的策略回测框架，支持：
- 多空双向交易模拟
- 手续费、滑点模拟
- 净值曲线与绩效分析
- SSE 实时进度推送
- 策略回调钩子 (notify_order/notify_trade)
- DataFeed 数据抽象（支持单/多资产）
- 衍生品数据访问（资金费率、市场情绪）

核心组件：
- BacktestEngine: 回测引擎核心
- BacktestAnalyzer: 绩效分析器
- BacktestBroker: 经纪商抽象
- DataFeed: 数据源抽象
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
from .broker import BacktestBroker
from .feed import DataFeed, SingleFeed, MultiFeed, create_feed
from .loader import validate_strategy_code, execute_strategy_code, load_strategy
from .strategy import Strategy

__all__ = [
    # Models
    "OrderSide",
    "OrderStatus",
    "OrderType",
    "Order",
    "Trade",
    "Position",
    "BacktestConfig",
    "BacktestResult",
    # Engine
    "BacktestEngine",
    "BacktestAnalyzer",
    "BacktestBroker",
    # Feed
    "DataFeed",
    "SingleFeed",
    "MultiFeed",
    "create_feed",
    # Loader
    "validate_strategy_code",
    "execute_strategy_code",
    "load_strategy",
    # Strategy
    "Strategy",
]
