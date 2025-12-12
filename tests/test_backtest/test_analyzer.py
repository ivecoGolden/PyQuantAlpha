# tests/test_backtest/test_analyzer.py
"""回测绩效分析器测试"""

import pytest
import math

from src.backtest.analyzer import BacktestAnalyzer
from src.backtest.models import Trade, OrderSide


class TestCalcTotalReturn:
    """总收益率计算测试"""
    
    def test_positive_return(self):
        result = BacktestAnalyzer._calc_total_return(100000, 120000)
        assert result == pytest.approx(0.2)
    
    def test_negative_return(self):
        result = BacktestAnalyzer._calc_total_return(100000, 90000)
        assert result == pytest.approx(-0.1)
    
    def test_zero_initial(self):
        result = BacktestAnalyzer._calc_total_return(0, 10000)
        assert result == 0.0


class TestCalcMaxDrawdown:
    """最大回撤计算测试"""
    
    def test_no_drawdown(self):
        # 单调上涨
        equities = [100, 110, 120, 130, 140]
        result = BacktestAnalyzer._calc_max_drawdown(equities)
        assert result == 0.0
    
    def test_simple_drawdown(self):
        # 100 -> 120 -> 90 (回撤 25%)
        equities = [100, 120, 90]
        result = BacktestAnalyzer._calc_max_drawdown(equities)
        assert result == pytest.approx(0.25)
    
    def test_multiple_drawdowns(self):
        # 100 -> 120 -> 100 -> 150 -> 100
        # 第一次回撤: (120-100)/120 = 16.67%
        # 第二次回撤: (150-100)/150 = 33.33%
        equities = [100, 120, 100, 150, 100]
        result = BacktestAnalyzer._calc_max_drawdown(equities)
        assert result == pytest.approx(1/3, rel=0.01)
    
    def test_empty_list(self):
        result = BacktestAnalyzer._calc_max_drawdown([])
        assert result == 0.0


class TestCalcSharpeRatio:
    """夏普比率计算测试"""
    
    def test_zero_volatility(self):
        # 净值不变
        equities = [100, 100, 100, 100]
        result = BacktestAnalyzer._calc_sharpe_ratio(equities)
        assert result == 0.0
    
    def test_positive_sharpe(self):
        # 稳定上涨
        equities = [100 + i * 0.5 for i in range(365)]
        result = BacktestAnalyzer._calc_sharpe_ratio(equities)
        assert result > 0
    
    def test_single_point(self):
        result = BacktestAnalyzer._calc_sharpe_ratio([100])
        assert result == 0.0


class TestCalcTradeStats:
    """交易统计测试"""
    
    def test_empty_trades(self):
        win_rate, profit_factor = BacktestAnalyzer._calc_trade_stats([])
        assert win_rate == 0.0
        assert profit_factor == 0.0
    
    def test_all_wins(self):
        trades = [
            Trade(id="1", order_id="O1", symbol="BTC", side=OrderSide.SELL,
                  price=100, quantity=1, fee=0, timestamp=0, pnl=100),
            Trade(id="2", order_id="O2", symbol="BTC", side=OrderSide.SELL,
                  price=100, quantity=1, fee=0, timestamp=0, pnl=50),
        ]
        win_rate, profit_factor = BacktestAnalyzer._calc_trade_stats(trades)
        assert win_rate == 1.0
        assert profit_factor == float('inf')
    
    def test_mixed_trades(self):
        trades = [
            Trade(id="1", order_id="O1", symbol="BTC", side=OrderSide.SELL,
                  price=100, quantity=1, fee=0, timestamp=0, pnl=100),
            Trade(id="2", order_id="O2", symbol="BTC", side=OrderSide.SELL,
                  price=100, quantity=1, fee=0, timestamp=0, pnl=-50),
        ]
        win_rate, profit_factor = BacktestAnalyzer._calc_trade_stats(trades)
        assert win_rate == 0.5
        assert profit_factor == 2.0  # 100 / 50


class TestAnalyze:
    """完整分析测试"""
    
    def test_empty_equity_curve(self):
        result = BacktestAnalyzer.analyze(100000, [], [])
        
        assert result.total_return == 0.0
        assert result.max_drawdown == 0.0
        assert result.total_trades == 0
    
    def test_simple_analysis(self):
        equity_curve = [
            {"timestamp": 1, "equity": 100000},
            {"timestamp": 2, "equity": 105000},
            {"timestamp": 3, "equity": 110000},
        ]
        
        result = BacktestAnalyzer.analyze(100000, equity_curve, [])
        
        assert result.total_return == pytest.approx(0.1)
        assert result.max_drawdown == 0.0
        assert result.total_trades == 0
