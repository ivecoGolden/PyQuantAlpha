# tests/test_backtest/test_engine.py
"""回测引擎测试"""

import pytest

from src.backtest.engine import BacktestEngine
from src.backtest.models import BacktestConfig, OrderSide
from src.data.models import Bar


# 模拟 K 线数据
def make_bars(prices: list[float], start_ts: int = 1000000) -> list[Bar]:
    """生成测试用 K 线数据"""
    return [
        Bar(
            timestamp=start_ts + i * 3600000,
            open=p,
            high=p * 1.01,
            low=p * 0.99,
            close=p,
            volume=1000.0
        )
        for i, p in enumerate(prices)
    ]


# 简单策略代码：第一根 K 线买入
SIMPLE_BUY_STRATEGY = '''
class Strategy:
    def init(self):
        self.bought = False
    
    def on_bar(self, bar):
        if not self.bought:
            self.order("BTCUSDT", "BUY", 1.0)
            self.bought = True
'''

# 买入后卖出策略：第 1 根买入，第 4 根卖出（订单在下一根 Bar 撮合）
SIMPLE_BUY_SELL_STRATEGY = '''
class Strategy:
    def init(self):
        self.bar_count = 0
    
    def on_bar(self, bar):
        self.bar_count += 1
        if self.bar_count == 1:
            self.order("BTCUSDT", "BUY", 1.0)  # 第 2 根成交
        elif self.bar_count == 4:
            self.close("BTCUSDT")  # 第 5 根成交
'''

EMA_CROSS_STRATEGY = '''
class Strategy:
    def init(self):
        self.ema_fast = EMA(3)
        self.ema_slow = EMA(5)
        self.prev_fast = None
        self.prev_slow = None
    
    def on_bar(self, bar):
        fast = self.ema_fast.update(bar.close)
        slow = self.ema_slow.update(bar.close)
        
        if fast is None or slow is None:
            return
        
        # 金叉买入
        if self.prev_fast and self.prev_slow:
            if self.prev_fast < self.prev_slow and fast > slow:
                pos = self.get_position("BTCUSDT")
                if not pos or pos.quantity == 0:
                    self.order("BTCUSDT", "BUY", 1.0)
            
            # 死叉卖出
            if self.prev_fast > self.prev_slow and fast < slow:
                pos = self.get_position("BTCUSDT")
                if pos and pos.quantity > 0:
                    self.close("BTCUSDT")
        
        self.prev_fast = fast
        self.prev_slow = slow
'''


class TestBacktestEngineBasic:
    """回测引擎基础功能测试"""
    
    def test_empty_data(self):
        """测试空数据"""
        engine = BacktestEngine()
        result = engine.run(SIMPLE_BUY_STRATEGY, [])
        
        assert result.total_trades == 0
        assert result.total_return == 0.0
    
    def test_simple_buy(self):
        """测试简单买入
        
        第 1 根 K 线下单，第 2 根撮合
        """
        bars = make_bars([50000, 51000, 52000])
        engine = BacktestEngine()
        
        result = engine.run(SIMPLE_BUY_STRATEGY, bars)
        
        # 应该有一笔买入交易
        assert result.total_trades == 1
        assert engine.positions["BTCUSDT"].quantity == 1.0
    
    def test_buy_and_sell(self):
        """测试买入后卖出
        
        第 1 根下买单 -> 第 2 根成交
        第 4 根下卖单 -> 第 5 根成交
        """
        # 5 根 K 线
        bars = make_bars([50000, 51000, 52000, 53000, 54000])
        engine = BacktestEngine()
        
        result = engine.run(SIMPLE_BUY_SELL_STRATEGY, bars)
        
        # 应该有两笔交易：买入 + 卖出
        assert result.total_trades == 2
        assert engine.positions["BTCUSDT"].quantity == 0
    
    def test_profit_calculation(self):
        """测试盈利计算
        
        第 1 根下单 (50000)，第 2 根成交 (51000)
        第 4 根下单平仓，第 5 根成交 (54000)
        盈利 = 54000 - 51000 = 3000
        """
        bars = make_bars([50000, 51000, 52000, 53000, 54000])
        config = BacktestConfig(
            initial_capital=100000,
            commission_rate=0,  # 简化计算
            slippage=0
        )
        engine = BacktestEngine(config)
        
        result = engine.run(SIMPLE_BUY_SELL_STRATEGY, bars)
        
        # 验证盈利
        pnl_trade = [t for t in result.trades if t.pnl != 0]
        assert len(pnl_trade) == 1
        assert pnl_trade[0].pnl == pytest.approx(3000, rel=0.01)


class TestBacktestEngineCommission:
    """手续费和滑点测试"""
    
    def test_commission_deducted(self):
        """测试手续费扣除
        
        第 1 根下单，第 2 根成交
        """
        bars = make_bars([50000, 50000])  # 两根 K 线
        config = BacktestConfig(
            initial_capital=100000,
            commission_rate=0.001,
            slippage=0
        )
        engine = BacktestEngine(config)
        
        engine.run(SIMPLE_BUY_STRATEGY, bars)
        
        # 买入 1 BTC @ 50000，手续费 = 50000 * 0.001 = 50
        # 剩余资金 = 100000 - 50000 - 50 = 49950
        assert engine.cash == pytest.approx(49950, rel=0.01)
    
    def test_slippage_applied(self):
        """测试滑点"""
        bars = make_bars([50000, 50000])  # 两根 K 线
        config = BacktestConfig(
            initial_capital=100000,
            commission_rate=0,
            slippage=0.001  # 0.1%
        )
        engine = BacktestEngine(config)
        
        engine.run(SIMPLE_BUY_STRATEGY, bars)
        
        # 买入滑点：50000 * 1.001 = 50050
        # 剩余资金 = 100000 - 50050 = 49950
        assert engine.cash == pytest.approx(49950, rel=0.01)


class TestBacktestEngineRejection:
    """订单拒绝测试"""
    
    def test_insufficient_funds(self):
        """测试资金不足拒绝"""
        bars = make_bars([50000, 50000])
        config = BacktestConfig(initial_capital=10000)  # 只有 1 万
        engine = BacktestEngine(config)
        
        result = engine.run(SIMPLE_BUY_STRATEGY, bars)
        
        # 买入 1 BTC @ 50000 需要 5 万，资金不足应被拒绝
        assert result.total_trades == 0
        assert engine.cash == 10000


class TestBacktestEngineEquity:
    """净值计算测试"""
    
    def test_equity_curve_length(self):
        """测试净值曲线长度"""
        bars = make_bars([50000, 51000, 52000])
        engine = BacktestEngine()
        
        result = engine.run(SIMPLE_BUY_STRATEGY, bars)
        
        assert len(result.equity_curve) == 3
    
    def test_equity_increases_with_price(self):
        """测试价格上涨净值增加
        
        第 1 根下单 (50000)，第 2 根成交 (60000)
        第 3 根：净值 = cash + position * price
        """
        bars = make_bars([50000, 60000, 70000])  # 价格上涨
        config = BacktestConfig(
            initial_capital=100000,
            commission_rate=0,
            slippage=0
        )
        engine = BacktestEngine(config)
        
        result = engine.run(SIMPLE_BUY_STRATEGY, bars)
        
        # 第 2 根 K 线买入成交: cash=40000, position=1 BTC @ 60000
        # 第 3 根 K 线：净值 = 40000 + 1 * 70000 = 110000
        final_equity = result.equity_curve[-1]["equity"]
        assert final_equity == pytest.approx(110000, rel=0.01)

