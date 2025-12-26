# src/backtest/analyzers/drawdown.py
"""
回撤分析器

计算最大回撤、回撤持续时间等回撤相关指标。
"""

from typing import List, Dict, Any

from .base import BaseAnalyzer, AnalyzerResult


class DrawdownAnalyzer(BaseAnalyzer):
    """回撤分析器
    
    计算：
    - 最大回撤 (Max Drawdown)
    - 最大回撤持续时间
    - 回撤恢复时间
    """
    
    def __init__(self) -> None:
        super().__init__(name="Drawdown")
    
    def calculate(
        self,
        equity_curve: List[Dict[str, Any]],
        trades: List[Any],
        initial_capital: float = 100000.0
    ) -> AnalyzerResult:
        """计算回撤指标"""
        if not equity_curve or len(equity_curve) < 2:
            return AnalyzerResult(
                name=self.name,
                value=0.0,
                details={"max_drawdown": 0.0, "max_drawdown_duration": 0}
            )
        
        equities = [e["equity"] for e in equity_curve]
        timestamps = [e["timestamp"] for e in equity_curve]
        
        # 计算最大回撤
        peak = equities[0]
        max_drawdown = 0.0
        max_drawdown_start = 0
        max_drawdown_end = 0
        
        current_drawdown_start = 0
        
        for i, equity in enumerate(equities):
            if equity > peak:
                peak = equity
                current_drawdown_start = i
            
            drawdown = (peak - equity) / peak if peak > 0 else 0
            
            if drawdown > max_drawdown:
                max_drawdown = drawdown
                max_drawdown_start = current_drawdown_start
                max_drawdown_end = i
        
        # 计算回撤持续时间（毫秒 -> 小时）
        if max_drawdown_end > max_drawdown_start:
            duration_ms = timestamps[max_drawdown_end] - timestamps[max_drawdown_start]
            duration_hours = duration_ms / (60 * 60 * 1000)
        else:
            duration_hours = 0
        
        return AnalyzerResult(
            name=self.name,
            value=max_drawdown,
            details={
                "max_drawdown": max_drawdown,
                "max_drawdown_percent": f"{max_drawdown:.2%}",
                "max_drawdown_duration_hours": duration_hours,
                "peak_equity": peak,
                "trough_equity": equities[max_drawdown_end] if max_drawdown_end < len(equities) else equities[-1]
            }
        )
