# src/backtest/broker.py
"""
回测经纪商抽象层

Phase 2.2: 从 Engine 中剥离资金管理和订单撮合逻辑。
Broker 负责:
- 资金管理 (cash, value)
- 持仓管理 (positions)
- 订单生命周期管理 (submit, cancel, process)
- 撮合逻辑 (市价/限价/止损)

设计参考: Backtrader 的 BackBroker 类
"""

import logging
from typing import Dict, List, Optional, Callable

from src.backtest.models import (
    Order, OrderSide, OrderType, OrderStatus,
    Trade, Position, BacktestConfig
)
from src.data.models import Bar
from src.messages.errorMessage import ErrorMessage

logger = logging.getLogger(__name__)


class BacktestBroker:
    """回测经纪商
    
    负责管理资金、持仓和订单撮合，与 Engine 解耦。
    
    Attributes:
        cash: 当前可用现金
        positions: 持仓字典 {symbol: Position}
        orders: 所有订单历史
        active_orders: 当前活跃挂单
        config: 回测配置
    """
    
    def __init__(self, config: BacktestConfig = None):
        """初始化 Broker
        
        Args:
            config: 回测配置，包含初始资金、手续费率等
        """
        self._config = config or BacktestConfig()
        self._initial_cash = self._config.initial_capital
        self._cash = self._initial_cash
        self._positions: Dict[str, Position] = {}
        self._orders: List[Order] = []
        self._orders_map: Dict[str, Order] = {}  # O(1) 订单查找
        self._active_orders: List[Order] = []
        self._trade_counter = 0
        
        # 回调函数，由 Engine 注入
        self._on_order_callback: Optional[Callable[[Order], None]] = None
        self._on_trade_callback: Optional[Callable[[Trade], None]] = None
    
    # ============ 属性访问 ============
    
    @property
    def cash(self) -> float:
        """当前现金"""
        return self._cash
    
    @property
    def positions(self) -> Dict[str, Position]:
        """持仓字典"""
        return self._positions
    
    @property
    def orders(self) -> List[Order]:
        """所有订单"""
        return self._orders
    
    @property
    def active_orders(self) -> List[Order]:
        """活跃挂单"""
        return self._active_orders
    
    def get_position(self, symbol: str) -> Optional[Position]:
        """获取指定交易对的持仓
        
        Args:
            symbol: 交易对
            
        Returns:
            Position 对象，如果无持仓返回 None
        """
        pos = self._positions.get(symbol)
        if pos and pos.quantity != 0:
            return pos
        return None
    
    def get_value(self, prices: Dict[str, float]) -> float:
        """计算账户总价值
        
        Args:
            prices: 各交易对当前价格 {symbol: price}
            
        Returns:
            账户总价值 (现金 + 持仓市值)
        """
        value = self._cash
        for symbol, position in self._positions.items():
            if position.quantity != 0 and symbol in prices:
                value += position.market_value(prices[symbol])
        return value
    
    # ============ 订单管理 ============
    
    def set_callbacks(
        self,
        on_order: Callable[[Order], None] = None,
        on_trade: Callable[[Trade], None] = None
    ) -> None:
        """设置回调函数
        
        Args:
            on_order: 订单状态变化回调
            on_trade: 成交回调
        """
        self._on_order_callback = on_order
        self._on_trade_callback = on_trade
    
    def submit_order(self, order: Order) -> Order:
        """提交订单
        
        进行预检（资金/持仓检查），通过后转入 SUBMITTED 状态。
        
        Args:
            order: 订单对象
            
        Returns:
            更新状态后的订单
        """
        # 状态转换: CREATED -> SUBMITTED
        order.status = OrderStatus.SUBMITTED
        self._orders.append(order)
        self._orders_map[order.id] = order  # O(1) 查找支持
        
        # 预检：资金/持仓检查
        if not self._validate_order(order):
            order.status = OrderStatus.REJECTED
            logger.warning(f"订单被拒绝: {order.id} - {order.error_msg}")
            self._notify_order(order)
            return order
        
        # 预检通过: SUBMITTED -> ACCEPTED
        order.status = OrderStatus.ACCEPTED
        self._active_orders.append(order)
        
        logger.debug(f"订单已接受: {order.id} {order.side.value} {order.symbol} {order.quantity}")
        return order
    
    def cancel_order(self, order: Order) -> bool:
        """取消订单
        
        Args:
            order: 要取消的订单
            
        Returns:
            是否成功取消
        """
        if order in self._active_orders:
            order.status = OrderStatus.CANCELED
            self._active_orders.remove(order)
            self._notify_order(order)
            logger.debug(f"订单已取消: {order.id}")
            return True
        return False
    
    def process_orders(self, bar: Bar, symbol: str = None) -> List[Trade]:
        """处理所有活跃订单
        
        在每个 Bar 到来时被 Engine 调用，检查所有挂单是否成交。
        
        Args:
            bar: 当前 K 线数据
            symbol: 交易对 (如果 bar 不包含 symbol 信息)
            
        Returns:
            本周期产生的成交列表
        """
        trades = []
        orders_to_remove = []
        
        for order in self._active_orders:
            # 匹配交易对
            if symbol and order.symbol != symbol:
                continue
            
            # 尝试撮合
            fill_price = self._try_match(order, bar)
            
            if fill_price is not None:
                # 执行成交
                trade = self._execute_fill(order, fill_price, bar.timestamp)
                if trade:
                    trades.append(trade)
                orders_to_remove.append(order)
        
        # 移除已成交订单
        for order in orders_to_remove:
            if order in self._active_orders:
                self._active_orders.remove(order)
        
        return trades
    
    # ============ 内部方法 ============
    
    def _validate_order(self, order: Order) -> bool:
        """验证订单有效性
        
        检查资金/持仓是否足够。
        
        Args:
            order: 订单
            
        Returns:
            是否有效
        """
        # 估算成本（使用限价或触发价作为参考）
        ref_price = order.price or order.trigger_price or 0
        if ref_price == 0:
            # 市价单无法预估，暂时通过
            return True
        
        estimated_cost = ref_price * order.quantity
        fee = estimated_cost * self._config.commission_rate
        
        if order.side == OrderSide.BUY:
            required = estimated_cost + fee
            if required > self._cash:
                order.error_msg = ErrorMessage.BACKTEST_INSUFFICIENT_FUNDS
                return False
        else:
            # 卖出时检查是否有足够持仓（如果是平仓）
            position = self._positions.get(order.symbol)
            if position and position.quantity > 0:
                # 有多头持仓，允许卖出
                pass
            else:
                # 开空需要保证金检查
                margin_required = estimated_cost + fee
                if margin_required > self._cash:
                    order.error_msg = ErrorMessage.BACKTEST_INSUFFICIENT_FUNDS
                    return False
        
        return True
    
    def _try_match(self, order: Order, bar: Bar) -> Optional[float]:
        """尝试撮合订单
        
        根据订单类型和当前 Bar 数据判断是否成交。
        
        Args:
            order: 订单
            bar: K 线数据
            
        Returns:
            成交价格，如果未成交返回 None
        """
        if order.order_type == OrderType.MARKET:
            # 市价单：以收盘价成交（模拟滑点）
            slippage = bar.close * self._config.slippage
            if order.side == OrderSide.BUY:
                return bar.close + slippage
            else:
                return bar.close - slippage
        
        elif order.order_type == OrderType.LIMIT:
            # 限价单
            if order.side == OrderSide.BUY:
                # 买入限价单：当 Low <= limit_price 时成交
                if bar.low <= order.price:
                    return min(order.price, bar.open)  # 优于限价时用开盘价
            else:
                # 卖出限价单：当 High >= limit_price 时成交
                if bar.high >= order.price:
                    return max(order.price, bar.open)
        
        elif order.order_type == OrderType.STOP:
            # 止损单：先检查触发，再市价成交
            if not order.triggered:
                if self._check_stop_trigger(order, bar):
                    order.triggered = True
                    logger.debug(f"止损单已触发: {order.id} @ {order.trigger_price}")
                return None  # 触发后下一 tick 成交
            else:
                # 已触发，市价成交
                slippage = bar.close * self._config.slippage
                if order.side == OrderSide.BUY:
                    return bar.close + slippage
                else:
                    return bar.close - slippage
        
        elif order.order_type == OrderType.STOP_LIMIT:
            # 止损限价单：先检查触发，再限价成交
            if not order.triggered:
                if self._check_stop_trigger(order, bar):
                    order.triggered = True
                    logger.debug(f"止损限价单已触发: {order.id} @ {order.trigger_price}")
                return None
            else:
                # 已触发，按限价逻辑成交
                if order.side == OrderSide.BUY:
                    if bar.low <= order.price:
                        return min(order.price, bar.open)
                else:
                    if bar.high >= order.price:
                        return max(order.price, bar.open)
        
        return None
    
    def _check_stop_trigger(self, order: Order, bar: Bar) -> bool:
        """检查止损单是否触发
        
        Args:
            order: 止损订单
            bar: K 线数据
            
        Returns:
            是否触发
        """
        if order.trigger_price is None:
            return False
        
        if order.side == OrderSide.BUY:
            # 买入止损：价格上涨突破触发价
            return bar.high >= order.trigger_price
        else:
            # 卖出止损：价格下跌跌破触发价
            return bar.low <= order.trigger_price
    
    def _execute_fill(self, order: Order, fill_price: float, timestamp: int) -> Optional[Trade]:
        """执行成交
        
        更新订单状态、资金和持仓。
        
        Args:
            order: 订单
            fill_price: 成交价格
            timestamp: 成交时间
            
        Returns:
            Trade 对象
        """
        fee = fill_price * order.quantity * self._config.commission_rate
        
        # 更新资金
        if order.side == OrderSide.BUY:
            cost = fill_price * order.quantity + fee
            if cost > self._cash:
                order.status = OrderStatus.REJECTED
                order.error_msg = ErrorMessage.BACKTEST_INSUFFICIENT_FUNDS
                self._notify_order(order)
                return None
            self._cash -= cost
        else:
            # 卖出
            position = self._positions.get(order.symbol)
            if position and position.quantity > 0:
                # 平多
                proceeds = fill_price * order.quantity - fee
                self._cash += proceeds
            else:
                # 开空（保证金检查）
                margin = fill_price * order.quantity + fee
                if margin > self._cash:
                    order.status = OrderStatus.REJECTED
                    order.error_msg = ErrorMessage.BACKTEST_INSUFFICIENT_FUNDS
                    self._notify_order(order)
                    return None
                # 开空收到卖出款项
                proceeds = fill_price * order.quantity - fee
                self._cash += proceeds
        
        # 更新持仓
        position = self._positions.setdefault(order.symbol, Position(order.symbol))
        delta = order.quantity if order.side == OrderSide.BUY else -order.quantity
        pnl = position.update(delta, fill_price)
        
        # 更新订单状态
        order.status = OrderStatus.FILLED
        order.filled_avg_price = fill_price
        order.filled_quantity = order.quantity
        order.fee = fee
        
        # 创建 Trade 记录
        self._trade_counter += 1
        trade = Trade(
            id=f"T{self._trade_counter:06d}",
            order_id=order.id,
            symbol=order.symbol,
            side=order.side,
            price=fill_price,
            quantity=order.quantity,
            fee=fee,
            timestamp=timestamp,
            pnl=pnl
        )
        
        # 触发回调
        self._notify_order(order)
        self._notify_trade(trade)
        
        logger.debug(
            f"成交: {order.symbol} {order.side.value} "
            f"{order.quantity} @ {fill_price:.2f}, PnL: {pnl:.2f}"
        )
        
        return trade
    
    def _notify_order(self, order: Order) -> None:
        """通知订单状态变化"""
        if self._on_order_callback:
            try:
                self._on_order_callback(order)
            except Exception as e:
                logger.warning(f"订单回调异常: {e}")
    
    def _notify_trade(self, trade: Trade) -> None:
        """通知成交"""
        if self._on_trade_callback:
            try:
                self._on_trade_callback(trade)
            except Exception as e:
                logger.warning(f"成交回调异常: {e}")
    
    def reset(self) -> None:
        """重置 Broker 状态"""
        self._cash = self._initial_cash
        self._positions.clear()
        self._orders.clear()
        self._orders_map.clear()
        self._active_orders.clear()
        self._trade_counter = 0
    
    def get_order(self, order_id: str) -> Optional[Order]:
        """根据 ID 获取订单 (O(1))
        
        Args:
            order_id: 订单 ID
            
        Returns:
            Order 对象，不存在则返回 None
        """
        return self._orders_map.get(order_id)
