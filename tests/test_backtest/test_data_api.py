# tests/test_backtest/test_data_api.py
"""历史数据接口测试"""

import pytest
from src.backtest.engine import BacktestEngine
from src.backtest.models import BacktestConfig
from src.data.models import Bar


class TestDataAPI:
    """数据访问 API 测试"""
    
    @pytest.fixture
    def bars(self):
        """生成测试数据"""
        return [
            Bar(timestamp=1000 + i, open=100, high=105, low=95, close=100 + i, volume=1000)
            for i in range(20)
        ]
    
    def test_get_bars_returns_history(self, bars):
        """测试 get_bars 返回历史数据"""
        strategy_code = """
class Strategy:
    def init(self):
        self.bar_count = 0
        self.history_length = 0
        
    def on_bar(self, bar):
        self.bar_count += 1
        history = self.get_bars(10)
        self.history_length = len(history)
"""
        engine = BacktestEngine()
        result = engine.run(strategy_code, bars)
        
        # 策略应该能访问历史数据
        assert engine._strategy.bar_count == 20
        # 最后一根 bar 时，应该有 10 根历史数据
        assert engine._strategy.history_length == 10
    
    def test_get_bars_with_small_lookback(self, bars):
        """测试 get_bars 小 lookback"""
        strategy_code = """
class Strategy:
    def init(self):
        self.histories = []
        
    def on_bar(self, bar):
        # 获取最近 5 根
        history = self.get_bars(5)
        self.histories.append(len(history))
"""
        engine = BacktestEngine()
        engine.run(strategy_code, bars)
        
        # 前几根数据不够 5 根
        assert engine._strategy.histories[0] == 1
        assert engine._strategy.histories[4] == 5
        assert engine._strategy.histories[10] == 5
    
    def test_get_bar_offset(self, bars):
        """测试 get_bar 偏移获取"""
        strategy_code = """
class Strategy:
    def init(self):
        self.prev_closes = []
        
    def on_bar(self, bar):
        # -1 是当前 bar（因为 on_bar 前已加入历史）
        # -2 才是前一根
        prev = self.get_bar(-2)
        if prev:
            self.prev_closes.append(prev.close)
        else:
            self.prev_closes.append(None)
"""
        engine = BacktestEngine()
        engine.run(strategy_code, bars)
        
        # 第一根没有前一根（-2 越界）
        assert engine._strategy.prev_closes[0] is None
        # 第二根的 -2 是第一根
        assert engine._strategy.prev_closes[1] == 100
        # 第三根的 -2 是第二根
        assert engine._strategy.prev_closes[2] == 101
    
    def test_get_bar_out_of_range(self, bars):
        """测试 get_bar 越界返回 None"""
        strategy_code = """
class Strategy:
    def init(self):
        self.result = None
        
    def on_bar(self, bar):
        # 尝试获取不存在的偏移
        self.result = self.get_bar(-100)
"""
        engine = BacktestEngine()
        engine.run(strategy_code, bars[:5])
        
        assert engine._strategy.result is None


class TestSymbolTracking:
    """交易对追踪测试"""
    
    @pytest.fixture
    def bars(self):
        """生成测试数据"""
        return [
            Bar(timestamp=1000 + i, open=100, high=105, low=95, close=100, volume=1000)
            for i in range(10)
        ]
    
    def test_single_symbol_tracked(self, bars):
        """测试单交易对追踪"""
        strategy_code = """
class Strategy:
    def init(self):
        pass
        
    def on_bar(self, bar):
        self.order("BTCUSDT", "BUY", 0.01)
"""
        engine = BacktestEngine()
        result = engine.run(strategy_code, bars)
        
        assert "BTCUSDT" in result.symbols
    
    def test_multiple_symbols_tracked(self, bars):
        """测试多交易对追踪"""
        strategy_code = """
class Strategy:
    def init(self):
        self.count = 0
        
    def on_bar(self, bar):
        self.count += 1
        if self.count == 1:
            self.order("BTCUSDT", "BUY", 0.01)
        elif self.count == 3:
            self.order("ETHUSDT", "BUY", 0.1)
        elif self.count == 5:
            self.order("BNBUSDT", "BUY", 1)
"""
        engine = BacktestEngine()
        result = engine.run(strategy_code, bars)
        
        assert len(result.symbols) == 3
        assert "BTCUSDT" in result.symbols
        assert "ETHUSDT" in result.symbols
        assert "BNBUSDT" in result.symbols
    
    def test_no_orders_no_symbols(self, bars):
        """测试无订单时无交易对"""
        strategy_code = """
class Strategy:
    def init(self):
        pass
        
    def on_bar(self, bar):
        pass
"""
        engine = BacktestEngine()
        result = engine.run(strategy_code, bars)
        
        assert result.symbols == []
    
    def test_result_has_logs(self, bars):
        """测试结果包含日志"""
        strategy_code = """
class Strategy:
    def init(self):
        pass
        
    def on_bar(self, bar):
        pass
"""
        engine = BacktestEngine(enable_logging=True)
        result = engine.run(strategy_code, bars)
        
        # 应该有与 bar 数量相同的日志条目
        assert len(result.logs) == 10
        assert result.logs[0].timestamp == 1000
    
    def test_logging_disabled(self, bars):
        """测试禁用日志"""
        strategy_code = """
class Strategy:
    def init(self):
        pass
        
    def on_bar(self, bar):
        pass
"""
        engine = BacktestEngine(enable_logging=False)
        result = engine.run(strategy_code, bars)
        
        assert len(result.logs) == 0
