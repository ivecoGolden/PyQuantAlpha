# src/backtest/analyzers/sharpe.py
"""
风险调整收益分析器

计算 Sharpe Ratio、Sortino Ratio、Calmar Ratio 等风险调整后收益指标。
"""

import math
from typing import List, Dict, Any

from .base import BaseAnalyzer, AnalyzerResult


class SharpeRatioAnalyzer(BaseAnalyzer):
    """夏普比率分析器
    
    Sharpe Ratio = (R - Rf) / σ
    
    其中：
    - R: 投资组合收益率
    - Rf: 无风险利率 (默认 0)
    - σ: 收益率标准差
    """
    
    def __init__(self, risk_free_rate: float = 0.0) -> None:
        super().__init__(name="Sharpe Ratio")
        self.risk_free_rate = risk_free_rate
    
    def calculate(
        self,
        equity_curve: List[Dict[str, Any]],
        trades: List[Any],
        initial_capital: float = 100000.0
    ) -> AnalyzerResult:
        """计算夏普比率"""
        if not equity_curve or len(equity_curve) < 2:
            return AnalyzerResult(name=self.name, value=0.0)
        
        equities = [e["equity"] for e in equity_curve]
        
        # 计算收益率序列
        returns = []
        for i in range(1, len(equities)):
            if equities[i - 1] > 0:
                ret = (equities[i] - equities[i - 1]) / equities[i - 1]
                returns.append(ret)
        
        if not returns:
            return AnalyzerResult(name=self.name, value=0.0)
        
        # 平均收益率
        mean_return = sum(returns) / len(returns)
        
        # 标准差
        variance = sum((r - mean_return) ** 2 for r in returns) / len(returns)
        std_dev = math.sqrt(variance)
        
        # 年化因子（假设小时级数据）
        annualization_factor = math.sqrt(24 * 365)
        
        # 夏普比率
        if std_dev > 0:
            sharpe = (mean_return - self.risk_free_rate / (24 * 365)) / std_dev * annualization_factor
        else:
            sharpe = 0.0
        
        return AnalyzerResult(
            name=self.name,
            value=sharpe,
            details={
                "sharpe_ratio": sharpe,
                "mean_return": mean_return,
                "std_dev": std_dev,
                "risk_free_rate": self.risk_free_rate,
                "num_periods": len(returns)
            }
        )


class SortinoRatioAnalyzer(BaseAnalyzer):
    """索提诺比率分析器
    
    Sortino Ratio = (R - Rf) / σd
    
    与 Sharpe Ratio 类似，但只考虑下行波动率。
    """
    
    def __init__(self, risk_free_rate: float = 0.0) -> None:
        super().__init__(name="Sortino Ratio")
        self.risk_free_rate = risk_free_rate
    
    def calculate(
        self,
        equity_curve: List[Dict[str, Any]],
        trades: List[Any],
        initial_capital: float = 100000.0
    ) -> AnalyzerResult:
        """计算索提诺比率"""
        if not equity_curve or len(equity_curve) < 2:
            return AnalyzerResult(name=self.name, value=0.0)
        
        equities = [e["equity"] for e in equity_curve]
        
        # 计算收益率序列
        returns = []
        for i in range(1, len(equities)):
            if equities[i - 1] > 0:
                ret = (equities[i] - equities[i - 1]) / equities[i - 1]
                returns.append(ret)
        
        if not returns:
            return AnalyzerResult(name=self.name, value=0.0)
        
        # 平均收益率
        mean_return = sum(returns) / len(returns)
        
        # 下行标准差（只考虑负收益）
        downside_returns = [r for r in returns if r < 0]
        if downside_returns:
            downside_variance = sum(r ** 2 for r in downside_returns) / len(returns)
            downside_std = math.sqrt(downside_variance)
        else:
            downside_std = 0.0
        
        # 年化因子
        annualization_factor = math.sqrt(24 * 365)
        
        # 索提诺比率
        if downside_std > 0:
            sortino = (mean_return - self.risk_free_rate / (24 * 365)) / downside_std * annualization_factor
        else:
            sortino = float('inf') if mean_return > 0 else 0.0
        
        return AnalyzerResult(
            name=self.name,
            value=sortino,
            details={
                "sortino_ratio": sortino,
                "mean_return": mean_return,
                "downside_std": downside_std,
                "num_downside_periods": len(downside_returns)
            }
        )


class CalmarRatioAnalyzer(BaseAnalyzer):
    """卡尔玛比率分析器
    
    Calmar Ratio = 年化收益率 / 最大回撤
    
    衡量单位风险的收益能力。
    """
    
    def __init__(self) -> None:
        super().__init__(name="Calmar Ratio")
    
    def calculate(
        self,
        equity_curve: List[Dict[str, Any]],
        trades: List[Any],
        initial_capital: float = 100000.0
    ) -> AnalyzerResult:
        """计算卡尔玛比率"""
        if not equity_curve or len(equity_curve) < 2:
            return AnalyzerResult(name=self.name, value=0.0)
        
        equities = [e["equity"] for e in equity_curve]
        timestamps = [e["timestamp"] for e in equity_curve]
        
        # 计算总收益率
        final_equity = equities[-1]
        total_return = (final_equity - initial_capital) / initial_capital
        
        # 计算年化收益率
        time_span_ms = timestamps[-1] - timestamps[0]
        days = max(1, time_span_ms / (24 * 60 * 60 * 1000))
        years = days / 365
        if years > 0:
            annualized_return = (1 + total_return) ** (1 / years) - 1
        else:
            annualized_return = total_return
        
        # 计算最大回撤
        peak = equities[0]
        max_drawdown = 0.0
        for equity in equities:
            if equity > peak:
                peak = equity
            drawdown = (peak - equity) / peak if peak > 0 else 0
            if drawdown > max_drawdown:
                max_drawdown = drawdown
        
        # 卡尔玛比率
        if max_drawdown > 0:
            calmar = annualized_return / max_drawdown
        else:
            calmar = float('inf') if annualized_return > 0 else 0.0
        
        return AnalyzerResult(
            name=self.name,
            value=calmar,
            details={
                "calmar_ratio": calmar,
                "annualized_return": annualized_return,
                "max_drawdown": max_drawdown
            }
        )
