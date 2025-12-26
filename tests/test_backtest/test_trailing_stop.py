# tests/test_backtest/test_trailing_stop.py
"""
移动止损测试
"""

import pytest
from dataclasses import dataclass

from src.backtest.broker import BacktestBroker
from src.backtest.models import (
    Order, OrderSide, OrderType, OrderStatus, BacktestConfig
)
from src.data.models import Bar


def create_bar(
    open: float = 100.0,
    high: float = 105.0,
    low: float = 95.0,
    close: float = 102.0,
    volume: float = 1000.0,
    timestamp: int = 1700000000000
) -> Bar:
    """创建测试用 Bar"""
    return Bar(
        timestamp=timestamp,
        open=open,
        high=high,
        low=low,
        close=close,
        volume=volume
    )


def create_trailing_stop_order(
    symbol: str = "BTCUSDT",
    side: OrderSide = OrderSide.SELL,
    quantity: float = 1.0,
    trail_amount: float | None = None,
    trail_percent: float | None = None
) -> Order:
    """创建移动止损订单"""
    return Order(
        id="O001",
        symbol=symbol,
        side=side,
        order_type=OrderType.STOP_TRAIL,
        quantity=quantity,
        trail_amount=trail_amount,
        trail_percent=trail_percent,
        highest_price=0.0,
        lowest_price=float('inf')
    )


class TestTrailingStopUpdate:
    """测试移动止损价格更新"""
    
    def test_sell_trail_updates_highest_price(self):
        """卖出移动止损应追踪最高价"""
        broker = BacktestBroker(BacktestConfig(initial_capital=100000))
        
        order = create_trailing_stop_order(
            side=OrderSide.SELL,
            trail_amount=10.0
        )
        broker.submit_order(order)
        
        # 初始状态
        assert order.highest_price == 0.0
        
        # 第一根 Bar：high=105
        bar1 = create_bar(high=105, low=100)
        broker.process_orders(bar1, "BTCUSDT")
        
        assert order.highest_price == 105.0
        assert order.trigger_price == 95.0  # 105 - 10
        
        # 第二根 Bar：high=110（更高）
        bar2 = create_bar(high=110, low=102, timestamp=1700000060000)
        broker.process_orders(bar2, "BTCUSDT")
        
        assert order.highest_price == 110.0
        assert order.trigger_price == 100.0  # 110 - 10
    
    def test_sell_trail_stop_price_only_moves_up(self):
        """卖出移动止损的止损价只能上移"""
        broker = BacktestBroker(BacktestConfig(initial_capital=100000))
        
        order = create_trailing_stop_order(
            side=OrderSide.SELL,
            trail_amount=10.0
        )
        broker.submit_order(order)
        
        # 第一根 Bar：high=110
        bar1 = create_bar(high=110, low=105)
        broker.process_orders(bar1, "BTCUSDT")
        assert order.trigger_price == 100.0  # 110 - 10
        
        # 第二根 Bar：high=105（更低，止损价不应下移）
        bar2 = create_bar(high=105, low=100, timestamp=1700000060000)
        broker.process_orders(bar2, "BTCUSDT")
        
        assert order.highest_price == 110.0  # 保持最高
        assert order.trigger_price == 100.0  # 止损价不变
    
    def test_sell_trail_percent(self):
        """测试百分比移动止损"""
        broker = BacktestBroker(BacktestConfig(initial_capital=100000))
        
        order = create_trailing_stop_order(
            side=OrderSide.SELL,
            trail_percent=0.05  # 5%
        )
        broker.submit_order(order)
        
        # high=100
        bar = create_bar(high=100, low=95)
        broker.process_orders(bar, "BTCUSDT")
        
        assert order.highest_price == 100.0
        assert order.trigger_price == 95.0  # 100 * (1 - 0.05)
    
    def test_buy_trail_updates_lowest_price(self):
        """买入移动止损应追踪最低价（空头保护）"""
        broker = BacktestBroker(BacktestConfig(initial_capital=100000))
        
        order = create_trailing_stop_order(
            side=OrderSide.BUY,
            trail_amount=10.0
        )
        broker.submit_order(order)
        
        # 第一根 Bar：low=95，high=98（不触发止损 105）
        bar1 = create_bar(high=98, low=95)
        broker.process_orders(bar1, "BTCUSDT")
        
        assert order.lowest_price == 95.0
        assert order.trigger_price == 105.0  # 95 + 10
        assert order.status == OrderStatus.ACCEPTED
        
        # 第二根 Bar：low=90（更低），high=95（不触发止损 100）
        bar2 = create_bar(high=95, low=90, timestamp=1700000060000)
        broker.process_orders(bar2, "BTCUSDT")
        
        assert order.lowest_price == 90.0
        assert order.trigger_price == 100.0  # 90 + 10
        assert order.status == OrderStatus.ACCEPTED


class TestTrailingStopTrigger:
    """测试移动止损触发"""
    
    def test_sell_trail_triggers_on_low(self):
        """卖出移动止损在价格跌破止损价时触发"""
        broker = BacktestBroker(BacktestConfig(initial_capital=100000, slippage=0))
        
        # 先建立多头持仓
        buy_order = Order(
            id="BUY001",
            symbol="BTCUSDT",
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=1.0
        )
        broker.submit_order(buy_order)
        bar_entry = create_bar(close=100)
        broker.process_orders(bar_entry, "BTCUSDT")
        
        # 创建移动止损
        order = create_trailing_stop_order(
            side=OrderSide.SELL,
            quantity=1.0,
            trail_amount=10.0
        )
        order.id = "TRAIL001"
        broker.submit_order(order)
        
        # 第一根 Bar：high=110，设置止损价为 100
        bar1 = create_bar(high=110, low=105, timestamp=1700000060000)
        broker.process_orders(bar1, "BTCUSDT")
        assert order.trigger_price == 100.0
        assert order.status == OrderStatus.ACCEPTED
        
        # 第二根 Bar：low=98（跌破止损价 100）
        bar2 = create_bar(high=105, low=98, timestamp=1700000120000)
        trades = broker.process_orders(bar2, "BTCUSDT")
        
        assert order.status == OrderStatus.FILLED
        assert len(trades) == 1
    
    def test_buy_trail_triggers_on_high(self):
        """买入移动止损在价格涨破止损价时触发"""
        broker = BacktestBroker(BacktestConfig(initial_capital=100000, slippage=0))
        
        # 先建立空头持仓（简化：直接设置）
        sell_order = Order(
            id="SELL001",
            symbol="BTCUSDT",
            side=OrderSide.SELL,
            order_type=OrderType.MARKET,
            quantity=1.0
        )
        broker.submit_order(sell_order)
        bar_entry = create_bar(close=100)
        broker.process_orders(bar_entry, "BTCUSDT")
        
        # 创建移动止损（买入平空）
        order = create_trailing_stop_order(
            side=OrderSide.BUY,
            quantity=1.0,
            trail_amount=10.0
        )
        order.id = "TRAIL002"
        broker.submit_order(order)
        
        # 第一根 Bar：low=90，设置止损价为 100
        bar1 = create_bar(high=95, low=90, timestamp=1700000060000)
        broker.process_orders(bar1, "BTCUSDT")
        assert order.trigger_price == 100.0
        assert order.status == OrderStatus.ACCEPTED
        
        # 第二根 Bar：high=102（涨破止损价 100）
        bar2 = create_bar(high=102, low=95, timestamp=1700000120000)
        trades = broker.process_orders(bar2, "BTCUSDT")
        
        assert order.status == OrderStatus.FILLED
        assert len(trades) == 1
