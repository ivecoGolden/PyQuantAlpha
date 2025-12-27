# src/backtest/engine.py
"""
回测引擎核心

事件驱动的回测引擎，模拟真实交易流程：
1. 加载策略代码 -> 注入交易 API
2. 遍历 K 线 -> 撮合订单 -> 更新持仓
3. 策略 on_bar 执行 -> 收集日志
4. 分析绩效 -> 返回结果

支持功能：
- 多空交易（开多/开空/平仓）
- 手续费、滑点模拟
- notify_order/notify_trade 回调钩子
- 历史数据访问 (get_bars/get_bar)
"""

import logging
from typing import List, Optional, Any, Callable, Union, Dict

from src.data.models import Bar
from src.data.repository import MarketDataRepository
from src.messages import ErrorMessage

from .loader import execute_strategy_code
from .feed import DataFeed, SingleFeed, create_feed

from .models import (
    Order,
    OrderSide,
    OrderType,
    Trade,
    Position,
    BacktestConfig,
    BacktestResult,
)
from .analyzer import BacktestAnalyzer
from .logger import BacktestLogger
from .broker import BacktestBroker


logger = logging.getLogger(__name__)


class BacktestEngine:
    """回测引擎
    
    事件驱动的回测引擎，模拟真实交易流程。
    
    Example:
        >>> engine = BacktestEngine()
        >>> result = engine.run(strategy_code, bars)
        >>> print(f"总收益率: {result.total_return:.2%}")
    """
    
    def __init__(self, config: Optional[BacktestConfig] = None, enable_logging: bool = True) -> None:
        """初始化回测引擎
        
        Args:
            config: 回测配置，默认使用 BacktestConfig()
            enable_logging: 是否启用详细日志记录
        """
        self.config = config or BacktestConfig()
        self.enable_logging = enable_logging
        self._reset()
    
    def _reset(self) -> None:
        """重置引擎状态"""
        # Phase 2.2: 资金和持仓由 Broker 管理
        self._broker = BacktestBroker(self.config)
        
        # 回测结果数据
        self.trades: List[Trade] = []
        self.equity_curve: List[dict] = []
        self._current_bar: Optional[Bar] = None
        self._current_timestamp: int = 0
        self._strategy = None
        self._order_counter = 0
        
        # 数据访问支持
        self._bar_history: List[Bar] = []  # K 线历史缓存（供策略回溯）
        self._symbols: set = set()         # 策略使用的交易对
        self._logger = BacktestLogger(enabled=self.enable_logging)
        
        # 衍生品数据仓库（同步访问）
        self._market_repo = MarketDataRepository()
    
    def run(
        self,
        strategy_code: str,
        data: Union[List[Bar], DataFeed],
        on_progress: Optional[Callable[[int, int, float, int], None]] = None
    ) -> BacktestResult:
        """运行回测
        
        Args:
            strategy_code: 策略代码字符串
            data: K 线数据（List[Bar] 或 DataFeed）
            on_progress: 进度回调 (current_index, total_length, equity, timestamp)
            
        Returns:
            BacktestResult 回测结果
            
        Raises:
            RuntimeError: 策略执行失败
        """
        self._reset()
        
        # 自动将 List 或 Dict 转换为 DataFeed
        if isinstance(data, DataFeed):
            feed = data
        else:
            feed = create_feed(data)
        
        if not feed or len(feed) == 0:
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
        total_bars = len(feed)
        for i, data_item in enumerate(feed):
            # 统一处理单/多资产数据
            if isinstance(data_item, dict):
                # MultiFeed: Dict[str, Bar]
                bars = data_item
                # 当前时间取所有 Bar 的最大时间戳（解决对齐时的各 Bar 时间戳不一致问题）
                current_timestamp = max(b.timestamp for b in bars.values())
                # 记录所有涉及的 symbol
                for s in bars.keys():
                    self._symbols.add(s)
            else:
                # SingleFeed: Bar
                sym = feed.symbols[0]
                bars = {sym: data_item}
                current_timestamp = data_item.timestamp
            
            self._current_bar = data_item  # 存对应的原始对象
            self._current_timestamp = current_timestamp
            self._bar_history.append(data_item)
            
            # 3.1 撮合订单 (遍历所有资产)
            for symbol, bar in bars.items():
                # DEFAULT 是 SingleFeed 的占位符，表示未指定 symbol
                # 传入 None 让 broker 跳过 symbol 过滤，撮合所有订单
                match_symbol = None if symbol == "DEFAULT" else symbol
                new_trades = self._broker.process_orders(bar, symbol=match_symbol)
                for trade in new_trades:
                    self.trades.append(trade)
                    self._on_trade_filled(trade)
            
            # 3.2 记录净值
            equity = self._calculate_equity(data_item)
            
            self.equity_curve.append({
                "timestamp": current_timestamp,
                "equity": equity
            })
            
            # 3.3 日志记录（支持多资产）
            if bars:
                # 构建持仓字典 {symbol: quantity}
                positions_dict = {
                    sym: pos.quantity 
                    for sym, pos in self._broker.positions.items() 
                    if pos.quantity != 0
                }
                # 多资产传入 Dict[str, Bar]，单资产传入 Bar
                bar_data = bars if len(bars) > 1 else list(bars.values())[0]
                self._logger.log_bar(bar_data, equity=equity, positions=positions_dict)
            
            # 如果有回调，上报进度
            if on_progress:
                on_progress(i + 1, total_bars, equity, current_timestamp)
            
            # 3.4 执行策略
            try:
                # 如果是多资产，传入 Dict；单资产传入 Bar
                self._strategy.on_bar(data_item)
            except Exception as e:
                # 某些策略可能只有 on_bar(bar)，给多资产时会报错
                logger.error(ErrorMessage.BACKTEST_STRATEGY_ERROR.format(error=e))
            
            # 3.5 提交日志条目
            self._logger.commit()
        
        # 4. 分析结果
        result = BacktestAnalyzer.analyze(
            self.config.initial_capital,
            self.equity_curve,
            self.trades
        )
        # 附加 symbols 和 logs
        result.symbols = list(self._symbols)
        result.logs = self._logger.get_entries()
        return result
    
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
        # 数据访问 API（供策略回溯历史数据）
        self._strategy.get_bars = self._api_get_bars
        self._strategy.get_bar = self._api_get_bar
        
        # 衍生品数据 API（同步版本）
        self._strategy.get_funding_rates = self._api_get_funding_rates
        self._strategy.get_sentiment = self._api_get_sentiment
        
        # Phase 3.3: Sizer 和高级订单 API
        self._strategy.setsizer = self._api_setsizer
        self._strategy.trailing_stop = self._api_trailing_stop
        self._strategy.buy_bracket = self._api_buy_bracket
        self._strategy.sell_bracket = self._api_sell_bracket
        
        # Phase 3.4: 资金配置 API
        self._strategy.set_capital = self._api_set_capital
        
        # Phase 2.1: 策略回调钩子
        # 如果策略没有定义这些方法，则使用空占位
        if not hasattr(self._strategy, 'notify_order'):
            self._strategy.notify_order = lambda order: None
        if not hasattr(self._strategy, 'notify_trade'):
            self._strategy.notify_trade = lambda trade: None
    
    def _on_trade_filled(self, trade: Trade) -> None:
        """处理成交后的回调和日志
        
        Args:
            trade: 成交记录
        """
        # 获取对应订单 (O(1) 查找)
        order = self._broker.get_order(trade.order_id)
        
        if order:
            # 触发策略回调 notify_order
            try:
                self._strategy.notify_order(order)
            except Exception as e:
                logger.warning(f"notify_order 回调异常: {e}")
            
            # 记录订单事件到日志
            self._logger.log_order_event(order, timestamp=trade.timestamp)
        
        # 如果平仓产生盈亏，触发 notify_trade
        if trade.pnl != 0:
            try:
                self._strategy.notify_trade(trade)
            except Exception as e:
                logger.warning(f"notify_trade 回调异常: {e}")
            # 记录交易事件
            self._logger.log_trade_event(trade)
    
    def _calculate_equity(self, bar_data: Union[Bar, Dict[str, Bar]]) -> float:
        """计算当前净值
        
        Args:
            bar_data: 当前 K 线数据 (Bar 或 Dict)
            
        Returns:
            账户净值
        """
        prices = {}
        if isinstance(bar_data, dict):
            prices = {s: b.close for s, b in bar_data.items()}
        elif isinstance(bar_data, Bar):
            # SingleFeed 模式：使用当前 Bar 的价格计算所有持仓的市值
            if self._symbols:
                 prices = {s: bar_data.close for s in self._symbols}
        
        return self._broker.get_value(prices) if prices else self._broker.cash
    
    def _generate_order_id(self) -> str:
        """生成订单 ID"""
        self._order_counter += 1
        return f"O{self._order_counter:06d}"
    

    
    # ============ 策略 API ============
    
    def _api_order(
        self,
        symbol: str,
        side: str,
        quantity: float,
        price: Optional[float] = None,
        exectype: str = None,
        trigger: Optional[float] = None
    ) -> Order:
        """下单 API
        
        Phase 2.2: 使用 Broker 管理订单
        
        Args:
            symbol: 交易对
            side: "BUY" 或 "SELL"
            quantity: 数量
            price: 限价单价格（可选，默认市价单）
            exectype: 订单类型 "MARKET", "LIMIT", "STOP", "STOP_LIMIT" (可选)
            trigger: 止损触发价格 (STOP/STOP_LIMIT 必填)
            
        Returns:
            Order 对象
        """
        # 确定订单类型
        if exectype:
            order_type = OrderType(exectype)
        elif price:
            order_type = OrderType.LIMIT
        else:
            order_type = OrderType.MARKET
        
        order = Order(
            id=self._generate_order_id(),
            symbol=symbol,
            side=OrderSide(side),
            order_type=order_type,
            quantity=quantity,
            price=price,
            trigger_price=trigger,
            created_at=self._current_timestamp
        )
        
        # Phase 2.2: 使用 Broker 提交订单
        self._broker.submit_order(order)
        self._symbols.add(symbol)  # 记录使用的交易对
        
        logger.debug(f"创建订单: {order.id} {symbol} {side} {quantity} type={order_type.value}")
        return order
    
    def _api_close(self, symbol: str) -> Optional[Order]:
        """平仓 API
        
        Args:
            symbol: 交易对
            
        Returns:
            Order 对象，如果无持仓返回 None
        """
        position = self._broker.get_position(symbol)
        if not position or position.quantity == 0:
            return None
        
        # 多头平仓：卖出
        # 空头平仓：买入
        side = "SELL" if position.quantity > 0 else "BUY"
        return self._api_order(symbol, side, abs(position.quantity))
    
    def _api_get_position(self, symbol: str) -> Optional[Position]:
        """获取持仓 API
        
        Args:
            symbol: 交易对
            
        Returns:
            Position 对象，如果无持仓或持仓数量为 0 则返回 None
        """
        return self._broker.get_position(symbol)
    
    def _api_get_cash(self) -> float:
        """获取可用资金"""
        return self._broker.cash
    
    def _api_get_equity(self) -> float:
        """获取账户净值"""
        if self._current_bar:
            return self._calculate_equity(self._current_bar)
        return self._broker.cash
    
    def _api_get_bars(self, symbol: Optional[str] = None, lookback: int = 100) -> Union[List[Bar], List[dict]]:
        """获取历史 K 线数据
        
        Args:
            symbol: 交易对 (可选，不指定则返回全部)
            lookback: 返回最近 N 根 K 线
            
        Returns:
            List[Bar] 或 List[Dict]
        """
        history_slice = self._bar_history[-lookback:]
        
        if symbol:
            result = []
            for item in history_slice:
                if isinstance(item, dict):
                    if symbol in item:
                        result.append(item[symbol])
                elif isinstance(item, Bar):
                    result.append(item)
            return result
        
        return history_slice
    
    def _api_get_bar(self, symbol: Optional[str] = None, offset: int = -1) -> Optional[Union[Bar, Dict[str, Bar]]]:
        """获取指定偏移的 K 线
        
        Args:
            symbol: 交易对 (可选)
            offset: 偏移量（-1 表示前一根）
            
        Returns:
            Bar 对象，或 MultiFeed 模式下的 Dict[str, Bar]
        """
        try:
            item = self._bar_history[offset]
            
            if symbol:
                if isinstance(item, dict):
                    return item.get(symbol)
                return item
            else:
                return item
                
        except IndexError:
            return None
    
    def _api_get_funding_rates(self, symbol: str, days: int = 7) -> list:
        """获取资金费率历史（同步版本）
        
        Args:
            symbol: 交易对，如 "BTCUSDT"
            days: 天数
            
        Returns:
            资金费率数据列表，每项包含属性: symbol, timestamp, funding_rate, mark_price
        """
        import asyncio
        
        # 计算时间范围
        end_time = self._current_timestamp if self._current_timestamp else int(__import__('time').time() * 1000)
        start_time = end_time - days * 24 * 60 * 60 * 1000
        
        try:
            # 同步包装异步方法
            return asyncio.run(
                self._market_repo.get_funding_rates(symbol, start_time, end_time)
            )
        except Exception as e:
            logger.warning(f"获取资金费率失败: {e}")
            return []
    
    def _api_get_sentiment(self, symbol: str, days: int = 1, period: str = "1h") -> list:
        """获取市场情绪数据（同步版本）
        
        Args:
            symbol: 交易对，如 "BTCUSDT"
            days: 天数
            period: 数据周期，如 "5m", "15m", "30m", "1h", "4h"
            
        Returns:
            市场情绪数据列表，每项包含属性: symbol, timestamp, long_short_ratio
        """
        import asyncio
        
        # 计算时间范围
        end_time = self._current_timestamp if self._current_timestamp else int(__import__('time').time() * 1000)
        start_time = end_time - days * 24 * 60 * 60 * 1000
        
        try:
            # 同步包装异步方法
            return asyncio.run(
                self._market_repo.get_sentiment(symbol, start_time, end_time, period)
            )
        except Exception as e:
            logger.warning(f"获取市场情绪失败: {e}")
            return []
    
    # ============ Phase 3.3: Sizer 和高级订单 API ============
    
    def _api_setsizer(self, sizer_type: str, **params) -> None:
        """设置仓位计算器
        
        Args:
            sizer_type: "fixed", "percent", "allin", "risk"
            **params: 对应参数
        """
        from .sizers import FixedSize, PercentSize, AllIn, RiskSize, SizerParams
        
        sizer_params = SizerParams(
            stake=params.get("stake", 1.0),
            percent=params.get("percent", 20.0),
            risk_percent=params.get("risk_percent", 2.0),
            atr_period=params.get("atr_period", 14),
            atr_multiplier=params.get("atr_multiplier", 2.0)
        )
        
        sizer_map = {
            "fixed": FixedSize,
            "percent": PercentSize,
            "allin": AllIn,
            "risk": RiskSize
        }
        
        sizer_cls = sizer_map.get(sizer_type.lower(), FixedSize)
        sizer = sizer_cls(sizer_params)
        sizer.set_broker(self._broker)
        
        # 如果是 RiskSize，尝试注入策略（用于 ATR 访问）
        if sizer_type.lower() == "risk" and self._strategy:
            sizer.set_strategy(self._strategy)
        
        self._broker.set_sizer(sizer)
        logger.debug(f"设置 Sizer: {sizer_type}")
    
    def _api_trailing_stop(
        self,
        symbol: str,
        size: float = None,
        trailamount: float = None,
        trailpercent: float = None
    ) -> Order:
        """创建移动止损订单
        
        Args:
            symbol: 交易对
            size: 数量（可选，默认使用当前持仓）
            trailamount: 固定金额追踪距离
            trailpercent: 百分比追踪距离
            
        Returns:
            Order 对象
        """
        # 确定数量
        if size is None:
            position = self._broker.get_position(symbol)
            if not position or position.quantity == 0:
                logger.warning(f"trailing_stop: 无持仓 {symbol}")
                return None
            size = abs(position.quantity)
            side = "SELL" if position.quantity > 0 else "BUY"
        else:
            side = "SELL"  # 默认卖出止损
        
        order = Order(
            id=self._generate_order_id(),
            symbol=symbol,
            side=OrderSide(side),
            order_type=OrderType.STOP_TRAIL,
            quantity=size,
            trail_amount=trailamount,
            trail_percent=trailpercent,
            highest_price=0.0,
            lowest_price=float('inf'),
            created_at=self._current_timestamp
        )
        
        self._broker.submit_order(order)
        self._symbols.add(symbol)
        logger.debug(f"创建移动止损: {order.id} {symbol}")
        return order
    
    def _api_buy_bracket(
        self,
        symbol: str,
        size: float = None,
        stopprice: float = None,
        limitprice: float = None
    ) -> tuple:
        """创建买入挂钩订单（主订单 + 止损 + 止盈）
        
        Args:
            symbol: 交易对
            size: 数量（可选，使用 Sizer 计算）
            stopprice: 止损价
            limitprice: 止盈价
            
        Returns:
            (main_order, stop_order, limit_order)
        """
        # 使用 Sizer 计算数量
        if size is None:
            size = self._broker.get_size(self._current_bar, isbuy=True)
            if size <= 0:
                size = 0.1  # 默认值
        
        # 主订单（买入）
        main_order = self._api_order(symbol, "BUY", size)
        
        # 生成 OCO ID
        stop_id = self._generate_order_id()
        limit_id = self._generate_order_id()
        
        # 止损订单（卖出）
        stop_order = Order(
            id=stop_id,
            symbol=symbol,
            side=OrderSide.SELL,
            order_type=OrderType.STOP,
            quantity=size,
            trigger_price=stopprice,
            parent_id=main_order.id,
            oco_id=limit_id,
            created_at=self._current_timestamp
        )
        
        # 止盈订单（限价卖出）
        limit_order = Order(
            id=limit_id,
            symbol=symbol,
            side=OrderSide.SELL,
            order_type=OrderType.LIMIT,
            quantity=size,
            price=limitprice,
            parent_id=main_order.id,
            oco_id=stop_id,
            created_at=self._current_timestamp
        )
        
        # 添加为子订单（等主订单成交后激活）
        self._broker.add_child_order(stop_order)
        self._broker.add_child_order(limit_order)
        
        logger.debug(f"创建买入挂钩订单: 主={main_order.id}, 止损={stop_id}, 止盈={limit_id}")
        return (main_order, stop_order, limit_order)
    
    def _api_sell_bracket(
        self,
        symbol: str,
        size: float = None,
        stopprice: float = None,
        limitprice: float = None
    ) -> tuple:
        """创建卖出挂钩订单（主订单 + 止损 + 止盈）
        
        Args:
            symbol: 交易对
            size: 数量
            stopprice: 止损价（高于入场价）
            limitprice: 止盈价（低于入场价）
            
        Returns:
            (main_order, stop_order, limit_order)
        """
        # 使用 Sizer 计算数量
        if size is None:
            size = self._broker.get_size(self._current_bar, isbuy=False)
            if size <= 0:
                size = 0.1  # 默认值
        
        # 主订单（卖出开空）
        main_order = self._api_order(symbol, "SELL", size)
        
        # 生成 OCO ID
        stop_id = self._generate_order_id()
        limit_id = self._generate_order_id()
        
        # 止损订单（买入平空）
        stop_order = Order(
            id=stop_id,
            symbol=symbol,
            side=OrderSide.BUY,
            order_type=OrderType.STOP,
            quantity=size,
            trigger_price=stopprice,
            parent_id=main_order.id,
            oco_id=limit_id,
            created_at=self._current_timestamp
        )
        
        # 止盈订单（限价买入平空）
        limit_order = Order(
            id=limit_id,
            symbol=symbol,
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            quantity=size,
            price=limitprice,
            parent_id=main_order.id,
            oco_id=stop_id,
            created_at=self._current_timestamp
        )
        
        # 添加为子订单
        self._broker.add_child_order(stop_order)
        self._broker.add_child_order(limit_order)
        
        logger.debug(f"创建卖出挂钩订单: 主={main_order.id}, 止损={stop_id}, 止盈={limit_id}")
        return (main_order, stop_order, limit_order)
    
    # ============ Phase 3.4: 资金配置 API ============
    
    def _api_set_capital(self, amount: float) -> None:
        """设置初始资金
        
        必须在 init() 方法中调用，用于覆盖默认的初始资金配置。
        
        Args:
            amount: 初始资金金额，必须大于 0
            
        Raises:
            ValueError: 如果金额无效
            
        Example:
            >>> class Strategy:
            ...     def init(self):
            ...         self.set_capital(50000)  # 设置为 5 万
        """
        if amount <= 0:
            raise ValueError(f"初始资金必须大于 0，收到: {amount}")
        
        if amount > 1e12:  # 防止溢出
            raise ValueError(f"初始资金超过上限 (1万亿)，收到: {amount}")
        
        # 更新配置
        self.config.initial_capital = amount
        
        # 更新 Broker 的现金和初始资金
        self._broker._cash = amount
        self._broker._initial_cash = amount
        
        logger.debug(f"设置初始资金: ${amount:,.2f}")
