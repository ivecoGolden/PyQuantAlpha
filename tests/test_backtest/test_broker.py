# tests/test_backtest/test_broker.py
"""Phase 2.2: BacktestBroker 单元测试"""

import pytest
from src.backtest.broker import BacktestBroker
from src.backtest.models import (
    Order, OrderSide, OrderType, OrderStatus, 
    Position, BacktestConfig
)
from src.data.models import Bar


def make_bar(timestamp: int, open_: float, high: float, low: float, close: float) -> Bar:
    """创建测试用 Bar"""
    return Bar(
        timestamp=timestamp,
        open=open_,
        high=high,
        low=low,
        close=close,
        volume=1000.0
    )


class TestBrokerBasic:
    """Broker 基本功能测试"""
    
    def test_initial_state(self):
        """测试初始状态"""
        broker = BacktestBroker()
        
        assert broker.cash == 100000.0
        assert len(broker.positions) == 0
        assert len(broker.orders) == 0
        assert len(broker.active_orders) == 0
    
    def test_custom_config(self):
        """测试自定义配置"""
        config = BacktestConfig(initial_capital=50000.0)
        broker = BacktestBroker(config)
        
        assert broker.cash == 50000.0
    
    def test_reset(self):
        """测试重置功能"""
        broker = BacktestBroker()
        broker._cash = 50000.0
        broker._positions["BTC"] = Position("BTC", 1.0, 100.0)
        
        broker.reset()
        
        assert broker.cash == 100000.0
        assert len(broker.positions) == 0


class TestOrderSubmission:
    """订单提交测试"""
    
    def test_submit_market_order(self):
        """提交市价单"""
        broker = BacktestBroker()
        order = Order(
            id="O001",
            symbol="BTCUSDT",
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=1.0
        )
        
        result = broker.submit_order(order)
        
        assert result.status == OrderStatus.ACCEPTED
        assert order in broker.active_orders
        assert order in broker.orders
    
    def test_submit_limit_order(self):
        """提交限价单"""
        broker = BacktestBroker()
        order = Order(
            id="O002",
            symbol="BTCUSDT",
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            quantity=1.0,
            price=50000.0
        )
        
        result = broker.submit_order(order)
        
        assert result.status == OrderStatus.ACCEPTED
    
    def test_submit_insufficient_funds(self):
        """资金不足拒单"""
        config = BacktestConfig(initial_capital=1000.0)
        broker = BacktestBroker(config)
        
        order = Order(
            id="O003",
            symbol="BTCUSDT",
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            quantity=1.0,
            price=50000.0  # 需要 50000，只有 1000
        )
        
        result = broker.submit_order(order)
        
        assert result.status == OrderStatus.REJECTED
        assert order not in broker.active_orders


class TestOrderMatching:
    """订单撮合测试"""
    
    def test_market_order_fill(self):
        """市价单成交"""
        broker = BacktestBroker()
        order = Order(
            id="O001",
            symbol="BTCUSDT",
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=0.1
        )
        broker.submit_order(order)
        
        bar = make_bar(1000, 100.0, 105.0, 95.0, 100.0)
        trades = broker.process_orders(bar, "BTCUSDT")
        
        assert len(trades) == 1
        assert order.status == OrderStatus.FILLED
        assert order not in broker.active_orders
    
    def test_limit_buy_order_fill(self):
        """限价买单成交 - 价格低于限价"""
        broker = BacktestBroker()
        order = Order(
            id="O002",
            symbol="BTCUSDT",
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            quantity=0.1,
            price=100.0
        )
        broker.submit_order(order)
        
        # Low = 95 <= 100 (limit price), 应成交
        bar = make_bar(1000, 98.0, 105.0, 95.0, 100.0)
        trades = broker.process_orders(bar, "BTCUSDT")
        
        assert len(trades) == 1
        assert order.status == OrderStatus.FILLED
    
    def test_limit_buy_order_no_fill(self):
        """限价买单未成交 - 价格高于限价"""
        broker = BacktestBroker()
        order = Order(
            id="O003",
            symbol="BTCUSDT",
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            quantity=0.1,
            price=90.0  # 限价 90
        )
        broker.submit_order(order)
        
        # Low = 95 > 90 (limit price), 不成交
        bar = make_bar(1000, 98.0, 105.0, 95.0, 100.0)
        trades = broker.process_orders(bar, "BTCUSDT")
        
        assert len(trades) == 0
        assert order.status == OrderStatus.ACCEPTED  # 仍挂单


class TestStopOrders:
    """止损单测试"""
    
    def test_stop_buy_trigger(self):
        """止损买单触发"""
        broker = BacktestBroker()
        order = Order(
            id="O001",
            symbol="BTCUSDT",
            side=OrderSide.BUY,
            order_type=OrderType.STOP,
            quantity=0.1,
            trigger_price=105.0  # 突破 105 触发
        )
        broker.submit_order(order)
        
        # 第一根 K 线: High = 103 < 105, 不触发
        bar1 = make_bar(1000, 100.0, 103.0, 99.0, 102.0)
        trades = broker.process_orders(bar1, "BTCUSDT")
        assert len(trades) == 0
        assert not order.triggered
        
        # 第二根 K 线: High = 106 >= 105, 触发
        bar2 = make_bar(2000, 102.0, 106.0, 101.0, 105.0)
        trades = broker.process_orders(bar2, "BTCUSDT")
        assert order.triggered
        assert len(trades) == 0  # 触发后下一 tick 成交
        
        # 第三根 K 线: 成交
        bar3 = make_bar(3000, 105.0, 108.0, 104.0, 107.0)
        trades = broker.process_orders(bar3, "BTCUSDT")
        assert len(trades) == 1
        assert order.status == OrderStatus.FILLED
    
    def test_stop_sell_trigger(self):
        """止损卖单触发 (止损出场)"""
        broker = BacktestBroker()
        
        # 先建立多头持仓
        broker._positions["BTCUSDT"] = Position("BTCUSDT", 1.0, 100.0)
        
        order = Order(
            id="O002",
            symbol="BTCUSDT",
            side=OrderSide.SELL,
            order_type=OrderType.STOP,
            quantity=1.0,
            trigger_price=95.0  # 跌破 95 止损
        )
        broker.submit_order(order)
        
        # 第一根 K 线: Low = 96 > 95, 不触发
        bar1 = make_bar(1000, 100.0, 102.0, 96.0, 98.0)
        trades = broker.process_orders(bar1, "BTCUSDT")
        assert not order.triggered
        
        # 第二根 K 线: Low = 94 <= 95, 触发
        bar2 = make_bar(2000, 98.0, 99.0, 94.0, 95.0)
        trades = broker.process_orders(bar2, "BTCUSDT")
        assert order.triggered
        
        # 第三根 K 线: 成交
        bar3 = make_bar(3000, 95.0, 96.0, 93.0, 94.0)
        trades = broker.process_orders(bar3, "BTCUSDT")
        assert len(trades) == 1
        assert order.status == OrderStatus.FILLED


class TestCancelOrder:
    """取消订单测试"""
    
    def test_cancel_active_order(self):
        """取消活跃订单"""
        broker = BacktestBroker()
        order = Order(
            id="O001",
            symbol="BTCUSDT",
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            quantity=0.1,
            price=90.0
        )
        broker.submit_order(order)
        
        result = broker.cancel_order(order)
        
        assert result is True
        assert order.status == OrderStatus.CANCELED
        assert order not in broker.active_orders


class TestPositionManagement:
    """持仓管理测试"""
    
    def test_get_position(self):
        """获取持仓"""
        broker = BacktestBroker()
        broker._positions["BTCUSDT"] = Position("BTCUSDT", 1.0, 100.0)
        
        pos = broker.get_position("BTCUSDT")
        
        assert pos is not None
        assert pos.quantity == 1.0
    
    def test_get_position_none(self):
        """无持仓返回 None"""
        broker = BacktestBroker()
        
        pos = broker.get_position("BTCUSDT")
        
        assert pos is None
    
    def test_get_value(self):
        """计算账户价值"""
        broker = BacktestBroker()
        broker._cash = 50000.0
        broker._positions["BTCUSDT"] = Position("BTCUSDT", 1.0, 100.0)
        
        value = broker.get_value({"BTCUSDT": 110.0})
        
        # 50000 + 1 * 110 = 50110
        assert value == 50110.0
