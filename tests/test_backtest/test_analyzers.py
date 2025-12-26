# tests/test_backtest/test_analyzers.py
"""
分析器模块测试

测试各种分析器的计算逻辑。
"""

import pytest
import math
from src.backtest.analyzers import (
    BaseAnalyzer,
    AnalyzerResult,
    ReturnsAnalyzer,
    DrawdownAnalyzer,
    SharpeRatioAnalyzer,
    SortinoRatioAnalyzer,
    CalmarRatioAnalyzer,
    TradesAnalyzer,
    run_all_analyzers,
)


def create_equity_curve(values: list, start_ts: int = 1700000000000, interval_ms: int = 3600000) -> list:
    """创建测试用净值曲线"""
    return [
        {"timestamp": start_ts + i * interval_ms, "equity": v}
        for i, v in enumerate(values)
    ]


class MockTrade:
    """模拟交易对象"""
    def __init__(self, pnl: float):
        self.pnl = pnl


class TestAnalyzerResult:
    """测试分析器结果"""
    
    def test_basic_result(self):
        result = AnalyzerResult(name="Test", value=0.5)
        assert result.name == "Test"
        assert result.value == 0.5
        assert result.details is None
    
    def test_result_with_details(self):
        result = AnalyzerResult(name="Test", value=0.5, details={"key": "value"})
        assert result.details == {"key": "value"}


class TestReturnsAnalyzer:
    """测试收益分析器"""
    
    def test_empty_equity_curve(self):
        analyzer = ReturnsAnalyzer()
        result = analyzer.calculate([], [])
        assert result.value == 0.0
    
    def test_positive_return(self):
        equity = create_equity_curve([100000, 105000, 110000])
        analyzer = ReturnsAnalyzer()
        result = analyzer.calculate(equity, [], initial_capital=100000)
        assert result.value == pytest.approx(0.1, rel=0.01)
        assert result.details["total_return"] == pytest.approx(0.1, rel=0.01)
    
    def test_negative_return(self):
        equity = create_equity_curve([100000, 95000, 90000])
        analyzer = ReturnsAnalyzer()
        result = analyzer.calculate(equity, [], initial_capital=100000)
        assert result.value == pytest.approx(-0.1, rel=0.01)
    
    def test_volatility_calculation(self):
        # 波动率为 0 的情况（净值不变）
        equity = create_equity_curve([100000, 100000, 100000])
        analyzer = ReturnsAnalyzer()
        result = analyzer.calculate(equity, [], initial_capital=100000)
        assert result.details["volatility"] == 0.0


class TestDrawdownAnalyzer:
    """测试回撤分析器"""
    
    def test_no_drawdown(self):
        # 单调上涨
        equity = create_equity_curve([100000, 110000, 120000])
        analyzer = DrawdownAnalyzer()
        result = analyzer.calculate(equity, [])
        assert result.value == 0.0
    
    def test_simple_drawdown(self):
        # 100000 -> 120000 -> 100000 (回撤 16.67%)
        equity = create_equity_curve([100000, 120000, 100000])
        analyzer = DrawdownAnalyzer()
        result = analyzer.calculate(equity, [])
        expected_dd = (120000 - 100000) / 120000
        assert result.value == pytest.approx(expected_dd, rel=0.01)
    
    def test_max_drawdown(self):
        # 选择最大回撤
        equity = create_equity_curve([100000, 110000, 105000, 115000, 100000])
        analyzer = DrawdownAnalyzer()
        result = analyzer.calculate(equity, [])
        # 最大回撤从 115000 到 100000 = 13.04%
        expected_dd = (115000 - 100000) / 115000
        assert result.value == pytest.approx(expected_dd, rel=0.01)


class TestSharpeRatioAnalyzer:
    """测试夏普比率分析器"""
    
    def test_empty_returns(self):
        analyzer = SharpeRatioAnalyzer()
        result = analyzer.calculate([], [])
        assert result.value == 0.0
    
    def test_positive_sharpe(self):
        # 稳定上涨
        equity = create_equity_curve([100000, 101000, 102000, 103000, 104000])
        analyzer = SharpeRatioAnalyzer()
        result = analyzer.calculate(equity, [])
        assert result.value > 0
    
    def test_volatile_returns(self):
        # 波动大
        equity = create_equity_curve([100000, 110000, 95000, 105000, 100000])
        analyzer = SharpeRatioAnalyzer()
        result = analyzer.calculate(equity, [])
        # 波动大，Sharpe 应该较低
        assert isinstance(result.value, float)


class TestSortinoRatioAnalyzer:
    """测试索提诺比率分析器"""
    
    def test_no_downside(self):
        # 只有正收益
        equity = create_equity_curve([100000, 101000, 102000, 103000])
        analyzer = SortinoRatioAnalyzer()
        result = analyzer.calculate(equity, [])
        # 无下行风险，Sortino 应该很大
        assert result.value == float('inf') or result.value > 10
    
    def test_with_downside(self):
        equity = create_equity_curve([100000, 95000, 100000, 105000])
        analyzer = SortinoRatioAnalyzer()
        result = analyzer.calculate(equity, [])
        assert isinstance(result.value, float)


class TestCalmarRatioAnalyzer:
    """测试卡尔玛比率分析器"""
    
    def test_no_drawdown_calmar(self):
        # 只涨不跌
        equity = create_equity_curve([100000, 110000, 120000])
        analyzer = CalmarRatioAnalyzer()
        result = analyzer.calculate(equity, [], initial_capital=100000)
        # 无回撤，Calmar 应该很大
        assert result.value == float('inf') or result.value > 10
    
    def test_calmar_calculation(self):
        # 有回撤
        equity = create_equity_curve([100000, 120000, 90000, 100000])
        analyzer = CalmarRatioAnalyzer()
        result = analyzer.calculate(equity, [], initial_capital=100000)
        # 回撤 25%，收益 0%
        assert result.details["max_drawdown"] == pytest.approx(0.25, rel=0.01)


class TestTradesAnalyzer:
    """测试交易分析器"""
    
    def test_no_trades(self):
        analyzer = TradesAnalyzer()
        result = analyzer.calculate([], [])
        assert result.details["total_trades"] == 0
        assert result.details["win_rate"] == 0.0
    
    def test_all_winning(self):
        trades = [MockTrade(100), MockTrade(200), MockTrade(50)]
        analyzer = TradesAnalyzer()
        result = analyzer.calculate([], trades)
        assert result.value == 1.0  # 100% 胜率
        assert result.details["winning_trades"] == 3
        assert result.details["profit_factor"] == float('inf')
    
    def test_all_losing(self):
        trades = [MockTrade(-100), MockTrade(-200), MockTrade(-50)]
        analyzer = TradesAnalyzer()
        result = analyzer.calculate([], trades)
        assert result.value == 0.0  # 0% 胜率
        assert result.details["losing_trades"] == 3
    
    def test_mixed_trades(self):
        trades = [MockTrade(100), MockTrade(-50), MockTrade(200), MockTrade(-30)]
        analyzer = TradesAnalyzer()
        result = analyzer.calculate([], trades)
        assert result.value == 0.5  # 50% 胜率
        assert result.details["profit_factor"] == pytest.approx(300 / 80, rel=0.01)


class TestRunAllAnalyzers:
    """测试批量分析"""
    
    def test_run_all(self):
        equity = create_equity_curve([100000, 105000, 110000, 105000, 115000])
        trades = [MockTrade(100), MockTrade(-50)]
        
        results = run_all_analyzers(equity, trades, initial_capital=100000)
        
        assert "Returns" in results
        assert "Drawdown" in results
        assert "Sharpe Ratio" in results
        assert "Sortino Ratio" in results
        assert "Calmar Ratio" in results
        assert "Trades" in results
