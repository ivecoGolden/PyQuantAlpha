# tests/test_backtest/test_bracket_order.py
"""
挂钩订单 (Bracket Order) 和 OCO 测试
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
    return Bar(
        timestamp=timestamp,
        open=open,
        high=high,
        low=low,
        close=close,
        volume=volume
    )


class TestChildOrderActivation:
    """测试子订单激活"""
    
    def test_child_order_pending_before_parent_fill(self):
        """父订单未成交时，子订单应保持待激活状态"""
        broker = BacktestBroker(BacktestConfig(initial_capital=100000))
        
        # 创建父订单（限价买入，价格设低）
        parent = Order(
            id="MAIN001",
            symbol="BTCUSDT",
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            quantity=1.0,
            price=90.0  # 低于市价，暂不成交
        )
        broker.submit_order(parent)
        
        # 创建子订单（止损）
        child = Order(
            id="STOP001",
            symbol="BTCUSDT",
            side=OrderSide.SELL,
            order_type=OrderType.STOP,
            quantity=1.0,
            trigger_price=88.0,
            parent_id="MAIN001"
        )
        broker.add_child_order(child)
        
        # 处理一根 Bar（价格高于限价，父订单不成交）
        bar = create_bar(low=95, high=105)
        broker.process_orders(bar, "BTCUSDT")
        
        # 父订单未成交，子订单应在 pending 列表中
        assert parent.status == OrderStatus.ACCEPTED
        assert child not in broker.active_orders
        assert child in broker._pending_child_orders
    
    def test_child_order_activated_after_parent_fill(self):
        """父订单成交后，子订单应被激活"""
        broker = BacktestBroker(BacktestConfig(initial_capital=100000))
        
        # 创建父订单（市价买入）
        parent = Order(
            id="MAIN001",
            symbol="BTCUSDT",
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=1.0
        )
        broker.submit_order(parent)
        
        # 创建子订单（止损）
        child = Order(
            id="STOP001",
            symbol="BTCUSDT",
            side=OrderSide.SELL,
            order_type=OrderType.STOP,
            quantity=1.0,
            trigger_price=95.0,
            parent_id="MAIN001"
        )
        broker.add_child_order(child)
        
        # 处理 Bar（父订单成交）
        bar = create_bar(close=100)
        broker.process_orders(bar, "BTCUSDT")
        
        # 父订单成交，子订单应被激活
        assert parent.status == OrderStatus.FILLED
        assert child in broker.active_orders
        assert child not in broker._pending_child_orders
        assert child.status == OrderStatus.ACCEPTED


class TestOCOCancellation:
    """测试 OCO (One-Cancels-Other) 逻辑"""
    
    def test_oco_cancels_on_fill(self):
        """当 OCO 组中一个订单成交时，另一个应被取消"""
        broker = BacktestBroker(BacktestConfig(initial_capital=100000))
        
        # 先建立持仓
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
        
        # 创建止损单
        stop_order = Order(
            id="STOP001",
            symbol="BTCUSDT",
            side=OrderSide.SELL,
            order_type=OrderType.STOP,
            quantity=1.0,
            trigger_price=95.0,
            oco_id="LIMIT001"
        )
        broker.submit_order(stop_order)
        
        # 创建止盈单（OCO 关联）
        limit_order = Order(
            id="LIMIT001",
            symbol="BTCUSDT",
            side=OrderSide.SELL,
            order_type=OrderType.LIMIT,
            quantity=1.0,
            price=110.0,
            oco_id="STOP001"
        )
        broker.submit_order(limit_order)
        
        # 触发止损单（low=94 < trigger=95）
        bar_trigger = create_bar(high=100, low=94, timestamp=1700000060000)
        # 先触发
        broker.process_orders(bar_trigger, "BTCUSDT")
        
        # 下一根 Bar 成交
        bar_fill = create_bar(high=100, low=92, timestamp=1700000120000)
        trades = broker.process_orders(bar_fill, "BTCUSDT")
        
        # 止损成交，止盈应被取消
        assert stop_order.status == OrderStatus.FILLED
        assert limit_order.status == OrderStatus.CANCELED
        assert "OCO" in limit_order.error_msg


class TestBracketOrderFlow:
    """测试完整的挂钩订单流程"""
    
    def test_bracket_stop_triggers_take_profit_canceled(self):
        """止损触发后止盈应被取消"""
        broker = BacktestBroker(BacktestConfig(initial_capital=100000, slippage=0))
        
        # 1. 主订单（买入）
        main_order = Order(
            id="MAIN001",
            symbol="BTCUSDT",
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=1.0
        )
        broker.submit_order(main_order)
        
        # 2. 止损子订单
        stop_order = Order(
            id="STOP001",
            symbol="BTCUSDT",
            side=OrderSide.SELL,
            order_type=OrderType.STOP,
            quantity=1.0,
            trigger_price=95.0,
            parent_id="MAIN001",
            oco_id="TAKE001"
        )
        broker.add_child_order(stop_order)
        
        # 3. 止盈子订单
        take_order = Order(
            id="TAKE001",
            symbol="BTCUSDT",
            side=OrderSide.SELL,
            order_type=OrderType.LIMIT,
            quantity=1.0,
            price=110.0,
            parent_id="MAIN001",
            oco_id="STOP001"
        )
        broker.add_child_order(take_order)
        
        # 入场（主订单成交，子订单激活）
        bar1 = create_bar(close=100)
        broker.process_orders(bar1, "BTCUSDT")
        
        assert main_order.status == OrderStatus.FILLED
        assert stop_order.status == OrderStatus.ACCEPTED
        assert take_order.status == OrderStatus.ACCEPTED
        
        # 触发止损
        bar2 = create_bar(high=100, low=94, timestamp=1700000060000)
        broker.process_orders(bar2, "BTCUSDT")  # 触发
        
        bar3 = create_bar(high=96, low=90, timestamp=1700000120000)
        broker.process_orders(bar3, "BTCUSDT")  # 成交
        
        assert stop_order.status == OrderStatus.FILLED
        assert take_order.status == OrderStatus.CANCELED
    
    def test_bracket_take_profit_triggers_stop_canceled(self):
        """止盈触发后止损应被取消"""
        broker = BacktestBroker(BacktestConfig(initial_capital=100000, slippage=0))
        
        # 1. 主订单
        main_order = Order(
            id="MAIN002",
            symbol="BTCUSDT",
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=1.0
        )
        broker.submit_order(main_order)
        
        # 2. 止损
        stop_order = Order(
            id="STOP002",
            symbol="BTCUSDT",
            side=OrderSide.SELL,
            order_type=OrderType.STOP,
            quantity=1.0,
            trigger_price=95.0,
            parent_id="MAIN002",
            oco_id="TAKE002"
        )
        broker.add_child_order(stop_order)
        
        # 3. 止盈
        take_order = Order(
            id="TAKE002",
            symbol="BTCUSDT",
            side=OrderSide.SELL,
            order_type=OrderType.LIMIT,
            quantity=1.0,
            price=105.0,
            parent_id="MAIN002",
            oco_id="STOP002"
        )
        broker.add_child_order(take_order)
        
        # 入场
        bar1 = create_bar(close=100)
        broker.process_orders(bar1, "BTCUSDT")
        
        # 触发止盈（high=106 > price=105）
        bar2 = create_bar(high=106, low=100, timestamp=1700000060000)
        broker.process_orders(bar2, "BTCUSDT")
        
        assert take_order.status == OrderStatus.FILLED
        assert stop_order.status == OrderStatus.CANCELED
