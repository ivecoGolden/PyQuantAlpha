# src/backtest/analyzers/returns.py
"""
收益分析器

计算总收益率、年化收益率、波动率等收益相关指标。
"""

import math
from typing import List, Dict, Any

from .base import BaseAnalyzer, AnalyzerResult


class ReturnsAnalyzer(BaseAnalyzer):
    """收益分析器
    
    计算：
    - 总收益率 (Total Return)
    - 年化收益率 (Annualized Return)
    - 波动率 (Volatility)
    - 日收益率序列 (Daily Returns)
    """
    
    def __init__(self) -> None:
        super().__init__(name="Returns")
    
    def calculate(
        self,
        equity_curve: List[Dict[str, Any]],
        trades: List[Any],
        initial_capital: float = 100000.0
    ) -> AnalyzerResult:
        """计算收益指标"""
        if not equity_curve or len(equity_curve) < 2:
            return AnalyzerResult(
                name=self.name,
                value=0.0,
                details={"total_return": 0.0, "annualized_return": 0.0, "volatility": 0.0}
            )
        
        # 提取净值序列
        equities = [e["equity"] for e in equity_curve]
        timestamps = [e["timestamp"] for e in equity_curve]
        
        # 总收益率
        final_equity = equities[-1]
        total_return = (final_equity - initial_capital) / initial_capital
        
        # 计算日收益率（假设每个数据点代表一个固定时间间隔）
        daily_returns = []
        for i in range(1, len(equities)):
            if equities[i - 1] > 0:
                ret = (equities[i] - equities[i - 1]) / equities[i - 1]
                daily_returns.append(ret)
        
        # 年化收益率（假设 252 个交易日，每天 24 小时 K 线）
        # 根据时间跨度计算实际天数
        if len(timestamps) >= 2:
            time_span_ms = timestamps[-1] - timestamps[0]
            days = max(1, time_span_ms / (24 * 60 * 60 * 1000))
            years = days / 365
            if years > 0:
                annualized_return = (1 + total_return) ** (1 / years) - 1
            else:
                annualized_return = total_return
        else:
            annualized_return = 0.0
        
        # 波动率（年化）
        if daily_returns:
            mean_return = sum(daily_returns) / len(daily_returns)
            variance = sum((r - mean_return) ** 2 for r in daily_returns) / len(daily_returns)
            std_dev = math.sqrt(variance)
            # 假设小时级数据，年化因子 = sqrt(24 * 365)
            volatility = std_dev * math.sqrt(24 * 365)
        else:
            volatility = 0.0
        
        return AnalyzerResult(
            name=self.name,
            value=total_return,
            details={
                "total_return": total_return,
                "annualized_return": annualized_return,
                "volatility": volatility,
                "final_equity": final_equity,
                "initial_capital": initial_capital,
                "num_periods": len(equity_curve)
            }
        )
