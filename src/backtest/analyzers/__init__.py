# src/backtest/analyzers/__init__.py
"""
分析器模块

提供专业级回测绩效分析功能。

Available Analyzers:
- ReturnsAnalyzer: 收益分析（总收益、年化收益、波动率）
- DrawdownAnalyzer: 回撤分析（最大回撤、持续时间）
- SharpeRatioAnalyzer: 夏普比率
- SortinoRatioAnalyzer: 索提诺比率
- CalmarRatioAnalyzer: 卡尔玛比率
- TradesAnalyzer: 交易分析（胜率、盈亏比）

Example:
    >>> from src.backtest.analyzers import SharpeRatioAnalyzer
    >>> analyzer = SharpeRatioAnalyzer()
    >>> result = analyzer.calculate(equity_curve, trades)
    >>> print(f"Sharpe Ratio: {result.value:.2f}")
"""

from .base import BaseAnalyzer, AnalyzerResult
from .returns import ReturnsAnalyzer
from .drawdown import DrawdownAnalyzer
from .sharpe import SharpeRatioAnalyzer, SortinoRatioAnalyzer, CalmarRatioAnalyzer
from .trades import TradesAnalyzer


__all__ = [
    # 基类
    "BaseAnalyzer",
    "AnalyzerResult",
    # 分析器
    "ReturnsAnalyzer",
    "DrawdownAnalyzer",
    "SharpeRatioAnalyzer",
    "SortinoRatioAnalyzer",
    "CalmarRatioAnalyzer",
    "TradesAnalyzer",
]


def run_all_analyzers(
    equity_curve: list,
    trades: list,
    initial_capital: float = 100000.0
) -> dict:
    """运行所有分析器并返回汇总结果
    
    Args:
        equity_curve: 净值曲线
        trades: 交易列表
        initial_capital: 初始资金
        
    Returns:
        dict: 分析结果汇总
    """
    analyzers = [
        ReturnsAnalyzer(),
        DrawdownAnalyzer(),
        SharpeRatioAnalyzer(),
        SortinoRatioAnalyzer(),
        CalmarRatioAnalyzer(),
        TradesAnalyzer(),
    ]
    
    results = {}
    for analyzer in analyzers:
        result = analyzer.calculate(equity_curve, trades, initial_capital)
        results[result.name] = {
            "value": result.value,
            "details": result.details
        }
    
    return results
