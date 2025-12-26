# src/backtest/analyzers/trades.py
"""
交易分析器

计算胜率、盈亏比、平均盈亏等交易相关指标。
"""

from typing import List, Dict, Any

from .base import BaseAnalyzer, AnalyzerResult


class TradesAnalyzer(BaseAnalyzer):
    """交易分析器
    
    计算：
    - 胜率 (Win Rate)
    - 盈亏比 (Profit Factor)
    - 平均盈利/亏损
    - 最大单笔盈利/亏损
    """
    
    def __init__(self) -> None:
        super().__init__(name="Trades")
    
    def calculate(
        self,
        equity_curve: List[Dict[str, Any]],
        trades: List[Any],
        initial_capital: float = 100000.0
    ) -> AnalyzerResult:
        """计算交易指标"""
        if not trades:
            return AnalyzerResult(
                name=self.name,
                value=0.0,
                details={"win_rate": 0.0, "profit_factor": 0.0, "total_trades": 0}
            )
        
        # 提取盈亏
        pnls = [getattr(t, 'pnl', 0) for t in trades]
        
        # 分类
        winning_trades = [p for p in pnls if p > 0]
        losing_trades = [p for p in pnls if p < 0]
        
        total_trades = len(pnls)
        winning_count = len(winning_trades)
        losing_count = len(losing_trades)
        
        # 胜率
        win_rate = winning_count / total_trades if total_trades > 0 else 0.0
        
        # 盈亏比
        total_profit = sum(winning_trades) if winning_trades else 0
        total_loss = abs(sum(losing_trades)) if losing_trades else 0
        profit_factor = total_profit / total_loss if total_loss > 0 else float('inf')
        
        # 平均盈亏
        avg_win = sum(winning_trades) / len(winning_trades) if winning_trades else 0
        avg_loss = sum(losing_trades) / len(losing_trades) if losing_trades else 0
        
        # 最大单笔
        max_win = max(winning_trades) if winning_trades else 0
        max_loss = min(losing_trades) if losing_trades else 0
        
        # 净盈亏
        net_pnl = sum(pnls)
        
        return AnalyzerResult(
            name=self.name,
            value=win_rate,
            details={
                "win_rate": win_rate,
                "profit_factor": profit_factor,
                "total_trades": total_trades,
                "winning_trades": winning_count,
                "losing_trades": losing_count,
                "total_profit": total_profit,
                "total_loss": total_loss,
                "net_pnl": net_pnl,
                "avg_win": avg_win,
                "avg_loss": avg_loss,
                "max_win": max_win,
                "max_loss": max_loss
            }
        )
