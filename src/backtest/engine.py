# src/backtest/engine.py
"""回测引擎核心"""

import uuid
import logging
from typing import Dict, List, Optional, Any, Callable

from src.data.models import Bar
from src.ai.validator import execute_strategy_code
from src.messages import ErrorMessage

from .models import (
    Order,
    OrderSide,
    OrderStatus,
    OrderType,
    Trade,
    Position,
    BacktestConfig,
    BacktestResult,
)
from .analyzer import BacktestAnalyzer


logger = logging.getLogger(__name__)


class BacktestEngine:
    """回测引擎
    
    事件驱动的回测引擎，模拟真实交易流程。
    
    Example:
        >>> engine = BacktestEngine()
        >>> result = engine.run(strategy_code, bars)
        >>> print(f"总收益率: {result.total_return:.2%}")
    """
    
    def __init__(self, config: Optional[BacktestConfig] = None) -> None:
        """初始化回测引擎
        
        Args:
            config: 回测配置，默认使用 BacktestConfig()
        """
        self.config = config or BacktestConfig()
        self._reset()
    
    def _reset(self) -> None:
        """重置引擎状态"""
        self.cash = self.config.initial_capital
        self.positions: Dict[str, Position] = {}
        self.pending_orders: List[Order] = []
        self.trades: List[Trade] = []
        self.equity_curve: List[dict] = []
        self._current_bar: Optional[Bar] = None
        self._strategy = None
        self._order_counter = 0
        self._trade_counter = 0
    
    def run(
        self,
        strategy_code: str,
        data: List[Bar],
        on_progress: Optional[Callable[[int, int, float, int], None]] = None
    ) -> BacktestResult:
        """运行回测
        
        Args:
            strategy_code: 策略代码字符串
            data: K 线数据列表
            on_progress: 进度回调 (current_index, total_length, equity, timestamp)
            
        Returns:
            BacktestResult 回测结果
            
        Raises:
            RuntimeError: 策略执行失败
        """
        self._reset()
        
        if not data:
            logger.warning(ErrorMessage.BACKTEST_DATA_EMPTY)
            return BacktestAnalyzer.analyze(
                self.config.initial_capital,
                self.equity_curve,
                self.trades
            )
        
        # 1. 加载策略
        self._load_strategy(strategy_code)
        
        # 2. 初始化策略
        try:
            self._strategy.init()
        except Exception as e:
            raise RuntimeError(ErrorMessage.BACKTEST_STRATEGY_INIT_FAILED.format(error=e))
        
        # 3. 遍历数据
        total_bars = len(data)
        for i, bar in enumerate(data):
            self._current_bar = bar
            
            # 3.1 撮合待处理订单
            self._match_orders(bar)
            
            # 3.2 记录净值
            equity = self._calculate_equity(bar)
            self.equity_curve.append({
                "timestamp": bar.timestamp,
                "equity": equity
            })
            
            # 如果有回调，上报进度
            if on_progress:
                on_progress(i + 1, total_bars, equity, bar.timestamp)
            
            # 3.3 执行策略 on_bar
            try:
                self._strategy.on_bar(bar)
            except Exception as e:
                logger.error(ErrorMessage.BACKTEST_STRATEGY_ERROR.format(error=e))
        
        # 继续回测，不中断
        
        # 4. 分析结果
        return BacktestAnalyzer.analyze(
            self.config.initial_capital,
            self.equity_curve,
            self.trades
        )
    
    def _load_strategy(self, strategy_code: str) -> None:
        """加载策略代码
        
        Args:
            strategy_code: 策略代码
        """
        # 使用 validator 的执行器获取策略实例
        self._strategy = execute_strategy_code(strategy_code)
        
        # 注入交易 API
        self._strategy.order = self._api_order
        self._strategy.close = self._api_close
        self._strategy.get_position = self._api_get_position
        self._strategy.get_cash = self._api_get_cash
        self._strategy.get_equity = self._api_get_equity
    
    def _match_orders(self, bar: Bar) -> None:
        """撮合订单
        
        使用当前 Bar 的收盘价进行撮合。
        
        Args:
            bar: 当前 K 线
        """
        filled_orders = []
        
        for order in self.pending_orders:
            # 计算成交价格（含滑点）
            if order.side == OrderSide.BUY:
                fill_price = bar.close * (1 + self.config.slippage)
            else:
                fill_price = bar.close * (1 - self.config.slippage)
            
            # 计算手续费
            fee = fill_price * order.quantity * self.config.commission_rate
            
            # 检查资金/持仓是否充足
            if order.side == OrderSide.BUY:
                # 判断是平空还是开多
                position = self.positions.get(order.symbol)
                if position and position.quantity < 0:
                    # 平空仓：返还保证金 + 计算盈亏
                    close_qty = min(order.quantity, abs(position.quantity))
                    # 平空亏损 = close_qty * (buy_price - avg_price)
                    # 这会在 position.update 中计算
                    # 需要足够的现金来买入
                    required_cash = fill_price * order.quantity + fee
                    if required_cash > self.cash:
                        order.status = OrderStatus.REJECTED
                        order.error_msg = ErrorMessage.BACKTEST_INSUFFICIENT_FUNDS
                        logger.warning(ErrorMessage.BACKTEST_ORDER_REJECTED.format(
                            order_id=order.id, reason=ErrorMessage.BACKTEST_INSUFFICIENT_FUNDS
                        ))
                        continue
                    self.cash -= required_cash
                else:
                    # 开多仓或加仓
                    required_cash = fill_price * order.quantity + fee
                    if required_cash > self.cash:
                        order.status = OrderStatus.REJECTED
                        order.error_msg = ErrorMessage.BACKTEST_INSUFFICIENT_FUNDS
                        logger.warning(ErrorMessage.BACKTEST_ORDER_REJECTED.format(
                            order_id=order.id, reason=ErrorMessage.BACKTEST_INSUFFICIENT_FUNDS
                        ))
                        continue
                    # 扣除资金
                    self.cash -= required_cash
            else:
                # SELL: 平多或开空
                position = self.positions.get(order.symbol)
                if position and position.quantity > 0:
                    # 有多头持仓：平多
                    if position.quantity >= order.quantity:
                        # 全部平仓或部分平仓，收到卖出款项
                        proceeds = fill_price * order.quantity - fee
                        self.cash += proceeds
                    else:
                        # 部分平多 + 开空
                        # 平多部分收到款项
                        close_qty = position.quantity
                        proceeds = fill_price * close_qty - fee
                        self.cash += proceeds
                        # 开空部分需要保证金
                        short_qty = order.quantity - close_qty
                        margin_required = fill_price * short_qty  # 100% 保证金
                        if margin_required > self.cash:
                            order.status = OrderStatus.REJECTED
                            order.error_msg = ErrorMessage.BACKTEST_INSUFFICIENT_FUNDS
                            logger.warning(ErrorMessage.BACKTEST_ORDER_REJECTED.format(
                                order_id=order.id, reason="开空保证金不足"
                            ))
                            continue
                        # 冻结保证金（不扣除，只是锁定）
                else:
                    # 无多头持仓：直接开空（需要保证金）
                    margin_required = fill_price * order.quantity + fee  # 100% 保证金
                    if margin_required > self.cash:
                        order.status = OrderStatus.REJECTED
                        order.error_msg = ErrorMessage.BACKTEST_INSUFFICIENT_FUNDS
                        logger.warning(ErrorMessage.BACKTEST_ORDER_REJECTED.format(
                            order_id=order.id, reason="开空保证金不足"
                        ))
                        continue
                    # 注意：开空不扣除现金，只是冻结保证金概念
                    # 但为了简化，我们扣除手续费
                    self.cash -= fee
            
            # 更新持仓
            position = self.positions.setdefault(order.symbol, Position(order.symbol))
            delta = order.quantity if order.side == OrderSide.BUY else -order.quantity
            pnl = position.update(delta, fill_price)
            
            # 更新订单状态
            order.status = OrderStatus.FILLED
            order.filled_avg_price = fill_price
            order.filled_quantity = order.quantity
            order.fee = fee
            
            # 记录成交
            trade = Trade(
                id=self._generate_trade_id(),
                order_id=order.id,
                symbol=order.symbol,
                side=order.side,
                price=fill_price,
                quantity=order.quantity,
                fee=fee,
                timestamp=bar.timestamp,
                pnl=pnl
            )
            self.trades.append(trade)
            filled_orders.append(order)
            
            logger.debug(
                f"成交: {order.symbol} {order.side.value} "
                f"{order.quantity} @ {fill_price:.2f}, PnL: {pnl:.2f}"
            )
        
        # 清空待处理订单
        self.pending_orders = []
    
    def _calculate_equity(self, bar: Bar) -> float:
        """计算当前净值
        
        Args:
            bar: 当前 K 线
            
        Returns:
            账户净值
        """
        equity = self.cash
        
        for position in self.positions.values():
            if position.quantity != 0:
                # 使用收盘价计算市值
                equity += position.market_value(bar.close)
        
        return equity
    
    def _generate_order_id(self) -> str:
        """生成订单 ID"""
        self._order_counter += 1
        return f"O{self._order_counter:06d}"
    
    def _generate_trade_id(self) -> str:
        """生成成交 ID"""
        self._trade_counter += 1
        return f"T{self._trade_counter:06d}"
    
    # ============ 策略 API ============
    
    def _api_order(
        self,
        symbol: str,
        side: str,
        quantity: float,
        price: Optional[float] = None
    ) -> Order:
        """下单 API
        
        Args:
            symbol: 交易对
            side: "BUY" 或 "SELL"
            quantity: 数量
            price: 限价单价格（可选，默认市价单）
            
        Returns:
            Order 对象
        """
        order = Order(
            id=self._generate_order_id(),
            symbol=symbol,
            side=OrderSide(side),
            order_type=OrderType.LIMIT if price else OrderType.MARKET,
            quantity=quantity,
            price=price,
            created_at=self._current_bar.timestamp if self._current_bar else 0
        )
        self.pending_orders.append(order)
        
        logger.debug(f"创建订单: {order.id} {symbol} {side} {quantity}")
        return order
    
    def _api_close(self, symbol: str) -> Optional[Order]:
        """平仓 API
        
        Args:
            symbol: 交易对
            
        Returns:
            Order 对象，如果无持仓返回 None
        """
        position = self.positions.get(symbol)
        if not position or position.quantity == 0:
            return None
        
        # 多头平仓：卖出
        # 空头平仓：买入（暂不支持空头）
        side = "SELL" if position.quantity > 0 else "BUY"
        return self._api_order(symbol, side, abs(position.quantity))
    
    def _api_get_position(self, symbol: str) -> Optional[Position]:
        """获取持仓 API
        
        Args:
            symbol: 交易对
            
        Returns:
            Position 对象，如果无持仓或持仓数量为 0 则返回 None
        """
        position = self.positions.get(symbol)
        if position is None or position.quantity == 0:
            return None
        return position
    
    def _api_get_cash(self) -> float:
        """获取可用资金"""
        return self.cash
    
    def _api_get_equity(self) -> float:
        """获取账户净值"""
        if self._current_bar:
            return self._calculate_equity(self._current_bar)
        return self.cash
