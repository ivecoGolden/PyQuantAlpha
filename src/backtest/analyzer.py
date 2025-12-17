# src/backtest/analyzer.py
"""
回测绩效分析

计算各项回测指标：
- 总收益率 / 年化收益率
- 最大回撤
- 夏普比率
- 胜率 / 盈亏比

算法说明：
- 年化收益 = (1 + 总收益)^(365/天数) - 1
- 夏普 = (年化收益 - 无风险利率) / 年化波动率
"""

import math
from typing import List, Optional
from dataclasses import dataclass

from .models import Trade, BacktestResult


class BacktestAnalyzer:
    """回测绩效分析器
    
    计算各项回测指标：收益率、最大回撤、夏普比率等。
    """
    
    # 年化交易日数（加密货币 365 天）
    TRADING_DAYS_PER_YEAR = 365
    # 无风险利率（年化）
    RISK_FREE_RATE = 0.02
    
    @classmethod
    def analyze(
        cls,
        initial_capital: float,
        equity_curve: List[dict],
        trades: List[Trade]
    ) -> BacktestResult:
        """分析回测结果
        
        Args:
            initial_capital: 初始资金
            equity_curve: 净值曲线 [{"timestamp": int, "equity": float}, ...]
            trades: 成交记录列表
            
        Returns:
            BacktestResult 绩效指标对象
        """
        if not equity_curve:
            return cls._empty_result()
        
        # 提取净值序列
        equities = [e["equity"] for e in equity_curve]
        
        # 总收益率
        total_return = cls._calc_total_return(initial_capital, equities[-1])
        
        # 年化收益率
        days = len(equity_curve)
        annualized_return = cls._calc_annualized_return(total_return, days)
        
        # 最大回撤
        max_drawdown = cls._calc_max_drawdown(equities)
        
        # 夏普比率
        sharpe_ratio = cls._calc_sharpe_ratio(equities)
        
        # 交易统计
        win_rate, profit_factor = cls._calc_trade_stats(trades)
        
        return BacktestResult(
            total_return=total_return,
            annualized_return=annualized_return,
            max_drawdown=max_drawdown,
            sharpe_ratio=sharpe_ratio,
            win_rate=win_rate,
            profit_factor=profit_factor,
            total_trades=len(trades),
            equity_curve=equity_curve,
            trades=trades
        )
    
    @classmethod
    def _calc_total_return(cls, initial: float, final: float) -> float:
        """计算总收益率"""
        if initial <= 0:
            return 0.0
        return (final - initial) / initial
    
    @classmethod
    def _calc_annualized_return(cls, total_return: float, days: int) -> float:
        """计算年化收益率
        
        公式: (1 + total_return) ^ (365 / days) - 1
        """
        if days <= 0:
            return 0.0
        return (1 + total_return) ** (cls.TRADING_DAYS_PER_YEAR / days) - 1
    
    @classmethod
    def _calc_max_drawdown(cls, equities: List[float]) -> float:
        """计算最大回撤
        
        公式: max((peak - trough) / peak)
        """
        if not equities:
            return 0.0
        
        max_dd = 0.0
        peak = equities[0]
        
        for equity in equities:
            if equity > peak:
                peak = equity
            
            if peak > 0:
                dd = (peak - equity) / peak
                max_dd = max(max_dd, dd)
        
        return max_dd
    
    @classmethod
    def _calc_sharpe_ratio(cls, equities: List[float]) -> float:
        """计算夏普比率
        
        公式: (年化收益率 - 无风险利率) / 年化波动率
        """
        if len(equities) < 2:
            return 0.0
        
        # 计算日收益率
        daily_returns = []
        for i in range(1, len(equities)):
            if equities[i - 1] > 0:
                ret = (equities[i] - equities[i - 1]) / equities[i - 1]
                daily_returns.append(ret)
        
        if not daily_returns:
            return 0.0
        
        # 平均日收益率
        mean_return = sum(daily_returns) / len(daily_returns)
        
        # 日收益率标准差
        variance = sum((r - mean_return) ** 2 for r in daily_returns) / len(daily_returns)
        std_return = math.sqrt(variance)
        
        if std_return == 0:
            return 0.0
        
        # 年化
        annualized_return = mean_return * cls.TRADING_DAYS_PER_YEAR
        annualized_std = std_return * math.sqrt(cls.TRADING_DAYS_PER_YEAR)
        
        return (annualized_return - cls.RISK_FREE_RATE) / annualized_std
    
    @classmethod
    def _calc_trade_stats(cls, trades: List[Trade]) -> tuple[float, float]:
        """计算交易统计
        
        Returns:
            (win_rate, profit_factor)
        """
        if not trades:
            return 0.0, 0.0
        
        # 只统计有盈亏的交易（平仓交易）
        pnl_trades = [t for t in trades if t.pnl != 0]
        
        if not pnl_trades:
            return 0.0, 0.0
        
        wins = [t for t in pnl_trades if t.pnl > 0]
        losses = [t for t in pnl_trades if t.pnl < 0]
        
        # 胜率
        win_rate = len(wins) / len(pnl_trades) if pnl_trades else 0.0
        
        # 盈亏比
        total_profit = sum(t.pnl for t in wins)
        total_loss = abs(sum(t.pnl for t in losses))
        
        profit_factor = total_profit / total_loss if total_loss > 0 else float('inf')
        
        return win_rate, profit_factor
    
    @classmethod
    def _empty_result(cls) -> BacktestResult:
        """返回空结果"""
        return BacktestResult(
            total_return=0.0,
            annualized_return=0.0,
            max_drawdown=0.0,
            sharpe_ratio=0.0,
            win_rate=0.0,
            profit_factor=0.0,
            total_trades=0,
            equity_curve=[],
            trades=[]
        )
