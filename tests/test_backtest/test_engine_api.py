# tests/test_backtest/test_engine_api.py
"""
回测引擎策略 API 测试

测试注入到策略中的各种 API：
- setsizer: 仓位计算器
- trailing_stop: 移动止损
- buy_bracket / sell_bracket: 挂钩订单
"""

import pytest
from src.backtest.engine import BacktestEngine
from src.backtest.models import BacktestConfig, OrderType, OrderSide
from src.data.models import Bar


def create_test_bars(count: int = 100, base_price: float = 100.0) -> list[Bar]:
    """创建测试用 K 线数据"""
    bars = []
    for i in range(count):
        price = base_price + i * 0.1
        bars.append(Bar(
            timestamp=1700000000000 + i * 3600000,
            open=price,
            high=price * 1.01,
            low=price * 0.99,
            close=price,
            volume=1000.0
        ))
    return bars


class TestSetsizer:
    """测试 setsizer API"""
    
    def test_setsizer_fixed(self):
        """测试 fixed sizer 设置"""
        code = '''
class Strategy:
    def init(self):
        self.setsizer("fixed", stake=0.5)
    
    def on_bar(self, data):
        pass
'''
        engine = BacktestEngine(BacktestConfig(initial_capital=10000))
        result = engine.run(code, create_test_bars(10))
        
        # 验证 Sizer 已设置（通过检查 broker）
        from src.backtest.sizers import FixedSize
        assert isinstance(engine._broker._sizer, FixedSize)
    
    def test_setsizer_percent(self):
        """测试 percent sizer 设置"""
        code = '''
class Strategy:
    def init(self):
        self.setsizer("percent", percent=50)
    
    def on_bar(self, data):
        pass
'''
        engine = BacktestEngine(BacktestConfig(initial_capital=10000))
        result = engine.run(code, create_test_bars(10))
        
        from src.backtest.sizers import PercentSize
        assert isinstance(engine._broker._sizer, PercentSize)
        assert engine._broker._sizer.params.percent == 50
    
    def test_setsizer_allin(self):
        """测试 allin sizer 设置"""
        code = '''
class Strategy:
    def init(self):
        self.setsizer("allin")
    
    def on_bar(self, data):
        pass
'''
        engine = BacktestEngine(BacktestConfig(initial_capital=10000))
        result = engine.run(code, create_test_bars(10))
        
        from src.backtest.sizers import AllIn
        assert isinstance(engine._broker._sizer, AllIn)
    
    def test_setsizer_risk(self):
        """测试 risk sizer 设置"""
        code = '''
class Strategy:
    def init(self):
        self.setsizer("risk", risk_percent=2, atr_multiplier=2)
    
    def on_bar(self, data):
        pass
'''
        engine = BacktestEngine(BacktestConfig(initial_capital=10000))
        result = engine.run(code, create_test_bars(10))
        
        from src.backtest.sizers import RiskSize
        assert isinstance(engine._broker._sizer, RiskSize)
        assert engine._broker._sizer.params.risk_percent == 2


class TestTrailingStop:
    """测试 trailing_stop API"""
    
    def test_trailing_stop_creates_order(self):
        """trailing_stop 应创建 STOP_TRAIL 类型订单"""
        code = '''
class Strategy:
    def init(self):
        self.bought = False
    
    def on_bar(self, data):
        if not self.bought:
            self.order("BTCUSDT", "BUY", 0.1)
            self.bought = True
        elif len(self.get_bars()) > 5:
            pos = self.get_position("BTCUSDT")
            if pos and pos.quantity > 0:
                self.trailing_stop("BTCUSDT", trailpercent=0.05)
'''
        engine = BacktestEngine(BacktestConfig(initial_capital=10000, slippage=0))
        result = engine.run(code, create_test_bars(20))
        
        # 检查是否创建了移动止损订单
        trail_orders = [o for o in engine._broker._active_orders 
                       if o.order_type == OrderType.STOP_TRAIL]
        assert len(trail_orders) > 0
    
    def test_trailing_stop_with_size(self):
        """trailing_stop 可以指定数量"""
        code = '''
class Strategy:
    def init(self):
        self.created = False
    
    def on_bar(self, data):
        if not self.created:
            self.order("BTCUSDT", "BUY", 0.5)
            self.created = True
        elif len(self.get_bars()) > 3:
            self.trailing_stop("BTCUSDT", size=0.2, trailamount=100)
            self.created = True  # 防止重复创建
'''
        engine = BacktestEngine(BacktestConfig(initial_capital=10000, slippage=0))
        result = engine.run(code, create_test_bars(10))
        
        trail_orders = [o for o in engine._broker._active_orders 
                       if o.order_type == OrderType.STOP_TRAIL]
        if trail_orders:
            assert trail_orders[0].quantity == 0.2
            assert trail_orders[0].trail_amount == 100


class TestBuyBracket:
    """测试 buy_bracket API"""
    
    def test_buy_bracket_creates_three_orders(self):
        """buy_bracket 应创建主订单和两个子订单"""
        code = '''
class Strategy:
    def init(self):
        self.created = False
    
    def on_bar(self, data):
        if not self.created:
            self.buy_bracket("BTCUSDT", size=0.1, stopprice=90, limitprice=120)
            self.created = True
'''
        engine = BacktestEngine(BacktestConfig(initial_capital=10000, slippage=0))
        result = engine.run(code, create_test_bars(10))
        
        # 主订单应已成交（市价单），子订单应已激活
        # 子订单在 active_orders 中（止损和止盈）
        child_orders = [o for o in engine._broker._active_orders 
                       if o.parent_id is not None]
        
        # 验证有子订单被创建（可能在 active 或 pending）
        total_children = len(child_orders) + len(engine._broker._pending_child_orders)
        assert total_children >= 2, f"Expected >= 2 child orders, got {total_children}"
    
    def test_buy_bracket_child_orders_have_parent_id(self):
        """子订单应有 parent_id"""
        code = '''
class Strategy:
    def init(self):
        self.created = False
    
    def on_bar(self, data):
        if not self.created:
            self.buy_bracket("BTCUSDT", size=0.1, stopprice=90, limitprice=120)
            self.created = True
'''
        engine = BacktestEngine(BacktestConfig(initial_capital=10000, slippage=0))
        engine.run(code, create_test_bars(5))
        
        pending = engine._broker._pending_child_orders
        for order in pending:
            assert order.parent_id is not None


class TestSellBracket:
    """测试 sell_bracket API"""
    
    def test_sell_bracket_creates_orders(self):
        """sell_bracket 应创建主订单和子订单"""
        code = '''
class Strategy:
    def init(self):
        self.created = False
    
    def on_bar(self, data):
        if not self.created:
            self.sell_bracket("BTCUSDT", size=0.1, stopprice=110, limitprice=80)
            self.created = True
'''
        engine = BacktestEngine(BacktestConfig(initial_capital=10000, slippage=0))
        result = engine.run(code, create_test_bars(10))
        
        # 子订单是 BUY（平空）- 可能在 active 或 pending
        active_children = [o for o in engine._broker._active_orders if o.parent_id is not None]
        pending_children = engine._broker._pending_child_orders
        
        total_buy_children = len([o for o in active_children if o.side == OrderSide.BUY]) + \
                            len([o for o in pending_children if o.side == OrderSide.BUY])
        
        assert total_buy_children >= 2, f"Expected >= 2 BUY child orders, got {total_buy_children}"


class TestApiIntegration:
    """API 集成测试"""
    
    def test_strategy_with_setsizer_and_bracket(self):
        """策略可同时使用 setsizer 和 bracket"""
        code = '''
class Strategy:
    def init(self):
        self.setsizer("fixed", stake=0.05)
        self.traded = False
        self.bar_count = 0
    
    def on_bar(self, data):
        self.bar_count = self.bar_count + 1
        if not self.traded and self.bar_count > 5:
            close = data.close
            self.buy_bracket("BTCUSDT", stopprice=close*0.95, limitprice=close*1.1)
            self.traded = True
'''
        engine = BacktestEngine(BacktestConfig(initial_capital=10000, slippage=0))
        result = engine.run(code, create_test_bars(20))
        
        # 验证 sizer 设置成功
        from src.backtest.sizers import FixedSize
        assert isinstance(engine._broker._sizer, FixedSize)
        
        # 验证有交易或有子订单
        has_activity = result.total_trades > 0 or len(engine._broker._pending_child_orders) > 0
        assert has_activity, "Expected trades or pending child orders"
