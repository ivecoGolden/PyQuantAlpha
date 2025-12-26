# src/backtest/models.py
"""
回测数据模型

核心模型：
- Order: 订单（市价/限价/止损/止损限价/移动止损）
- Trade: 成交记录
- Position: 持仓（支持多/空）
- BacktestConfig: 回测配置
- BacktestResult: 回测结果

枚举类型：
- OrderSide: BUY / SELL
- OrderType: MARKET / LIMIT / STOP / STOP_LIMIT / STOP_TRAIL
- OrderStatus: CREATED / SUBMITTED / ACCEPTED / PARTIAL / FILLED / CANCELED / REJECTED / EXPIRED
"""

from enum import Enum
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any


class OrderSide(Enum):
    """订单方向"""
    BUY = "BUY"
    SELL = "SELL"


class OrderStatus(Enum):
    """订单状态
    
    Phase 2.2 完整生命周期:
    CREATED -> SUBMITTED -> ACCEPTED -> PARTIAL/FILLED/CANCELED/REJECTED/EXPIRED
    """
    CREATED = "CREATED"        # 创建但未提交
    SUBMITTED = "SUBMITTED"    # 已提交给 Broker
    ACCEPTED = "ACCEPTED"      # Broker 已受理（预检通过）
    PARTIAL = "PARTIAL"        # 部分成交
    FILLED = "FILLED"          # 全部成交
    CANCELED = "CANCELED"      # 已取消
    REJECTED = "REJECTED"      # 已拒绝（资金不足/无效参数）
    EXPIRED = "EXPIRED"        # 已过期 (TTL/Day order)



class OrderType(Enum):
    """订单类型
    
    Phase 2.2 新增 STOP 和 STOP_LIMIT 类型用于止损/止盈策略
    Phase 3.3 新增 STOP_TRAIL 移动止损类型
    """
    MARKET = "MARKET"          # 市价单
    LIMIT = "LIMIT"            # 限价单
    STOP = "STOP"              # 止损单 (触价即市价)
    STOP_LIMIT = "STOP_LIMIT"  # 止损限价单 (触价即限价)
    STOP_TRAIL = "STOP_TRAIL"  # 移动止损单 (追踪止损)


@dataclass
class Order:
    """订单
    
    Attributes:
        id: 订单 ID
        symbol: 交易对
        side: 买卖方向
        order_type: 订单类型
        quantity: 数量
        price: 限价单价格（市价单为 None）
        trigger_price: 触发价格 (STOP/STOP_LIMIT/STOP_TRAIL)
        created_at: 创建时间戳
        status: 订单状态
        filled_avg_price: 成交均价
        filled_quantity: 成交数量
        fee: 手续费
        error_msg: 错误信息
        triggered: STOP 单是否已触发
        
        # Phase 3.3 新增
        parent_id: 父订单 ID（用于 Bracket Order）
        oco_id: OCO 关联订单 ID（One-Cancels-Other）
        trail_amount: 移动止损的固定金额距离
        trail_percent: 移动止损的百分比距离
        highest_price: 追踪期间的最高价（用于卖出时的移动止损）
        lowest_price: 追踪期间的最低价（用于买入时的移动止损）
    """
    id: str
    symbol: str
    side: OrderSide
    order_type: OrderType
    quantity: float
    price: Optional[float] = None
    trigger_price: Optional[float] = None  # 触发价格 (STOP/STOP_LIMIT)
    created_at: int = 0
    status: OrderStatus = OrderStatus.CREATED
    filled_avg_price: float = 0.0
    filled_quantity: float = 0.0
    fee: float = 0.0
    error_msg: str = ""
    triggered: bool = False  # STOP 单是否已触发
    # Phase 3.3 新增：挂钩订单和移动止损
    parent_id: Optional[str] = None       # 父订单 ID
    oco_id: Optional[str] = None          # OCO 关联订单 ID
    trail_amount: Optional[float] = None  # 移动止损固定金额
    trail_percent: Optional[float] = None # 移动止损百分比
    highest_price: float = 0.0            # 追踪期间最高价
    lowest_price: float = float('inf')    # 追踪期间最低价


@dataclass
class Trade:
    """成交记录
    
    Attributes:
        id: 成交 ID
        order_id: 关联订单 ID
        symbol: 交易对
        side: 买卖方向
        price: 成交价格
        quantity: 成交数量
        fee: 手续费
        timestamp: 成交时间戳
        pnl: 平仓盈亏（仅平仓时有值）
    """
    id: str
    order_id: str
    symbol: str
    side: OrderSide
    price: float
    quantity: float
    fee: float
    timestamp: int
    pnl: float = 0.0


@dataclass
class Position:
    """持仓
    
    Attributes:
        symbol: 交易对
        quantity: 持仓数量（正数多头，负数空头）
        avg_price: 持仓均价
    """
    symbol: str
    quantity: float = 0.0
    avg_price: float = 0.0
    
    def update(self, delta_quantity: float, price: float) -> float:
        """更新持仓
        
        Args:
            delta_quantity: 数量变化（正数买入，负数卖出）
            price: 成交价格
            
        Returns:
            平仓盈亏（如果是减仓/平仓）
        """
        pnl = 0.0
        
        if self.quantity == 0:
            # 新开仓
            self.avg_price = price
            self.quantity = delta_quantity
        elif (self.quantity > 0 and delta_quantity > 0) or \
             (self.quantity < 0 and delta_quantity < 0):
            # 同向加仓：更新均价
            total_cost = abs(self.quantity) * self.avg_price + abs(delta_quantity) * price
            self.quantity += delta_quantity
            if abs(self.quantity) > 1e-10:
                self.avg_price = total_cost / abs(self.quantity)
        else:
            # 减仓或反向开仓
            close_qty = min(abs(self.quantity), abs(delta_quantity))
            
            # 计算平仓盈亏
            if self.quantity > 0:
                # 原多头平仓
                pnl = close_qty * (price - self.avg_price)
            else:
                # 原空头平仓
                pnl = close_qty * (self.avg_price - price)
            
            self.quantity += delta_quantity
            
            # 如果反向开仓
            if abs(delta_quantity) > close_qty:
                self.avg_price = price
        
        # 清零判断
        if abs(self.quantity) < 1e-10:
            self.quantity = 0.0
            self.avg_price = 0.0
        
        return pnl
    
    def unrealized_pnl(self, current_price: float) -> float:
        """计算未实现盈亏
        
        Args:
            current_price: 当前价格
            
        Returns:
            未实现盈亏
        """
        if self.quantity == 0:
            return 0.0
        return self.quantity * (current_price - self.avg_price)
    
    def market_value(self, current_price: float) -> float:
        """计算持仓市值（用于净值计算）
        
        对于多头：市值 = 数量 * 当前价格
        对于空头：市值 = 未实现盈亏（因为开空时没有实际购买资产）
        
        Args:
            current_price: 当前价格
            
        Returns:
            持仓市值（多头为正，空头返回浮动盈亏）
        """
        if self.quantity > 0:
            # 多头：持有资产的市值
            return self.quantity * current_price
        elif self.quantity < 0:
            # 空头：返回浮动盈亏（开仓价 - 现价）* 数量
            # 空头盈利 = (avg_price - current_price) * abs(quantity)
            return abs(self.quantity) * (self.avg_price - current_price)
        return 0.0


@dataclass
class BacktestConfig:
    """回测配置
    
    Attributes:
        initial_capital: 初始资金
        commission_rate: 手续费率
        slippage: 滑点
    """
    initial_capital: float = 100000.0
    commission_rate: float = 0.001   # 0.1%
    slippage: float = 0.0005         # 0.05%


@dataclass
class BacktestLogEntry:
    """回测日志条目
    
    记录每一步的详细信息，便于调试和复盘。
    
    Attributes:
        timestamp: 时间戳
        bar_data: K线数据，单资产为 {open, high, low, close, volume}，
                  多资产为 {symbol: {open, high, low, close, volume}}
        indicators: 指标值 {"EMA20": 50000, "RSI": 45}
        signals: 触发的信号 ["Golden Cross"]
        orders: 本周期订单列表
        positions: 各资产持仓 {symbol: quantity}，空字典表示无持仓
        equity: 当前净值
        notes: 策略备注
    """
    timestamp: int
    bar_data: dict = field(default_factory=dict)
    indicators: dict = field(default_factory=dict)
    signals: List[str] = field(default_factory=list)
    orders: List[dict] = field(default_factory=list)
    positions: dict = field(default_factory=dict)  # 多资产持仓
    equity: float = 0.0
    notes: str = ""


@dataclass
class BacktestResult:
    """回测结果
    
    Attributes:
        total_return: 总收益率
        annualized_return: 年化收益率
        max_drawdown: 最大回撤
        sharpe_ratio: 夏普比率
        win_rate: 胜率
        profit_factor: 盈亏比
        total_trades: 总交易数
        sortino_ratio: 索提诺比率（仅考虑下行风险），可选
        calmar_ratio: 卡尔玛比率（年化收益/最大回撤），可选
        equity_curve: 净值曲线
        trades: 成交记录列表
        symbols: 策略使用的交易对列表
        logs: 详细日志条目
        analyzers_detail: 详细分析器输出（可选）
    """
    total_return: float
    annualized_return: float
    max_drawdown: float
    sharpe_ratio: float
    win_rate: float
    profit_factor: float
    total_trades: int
    # 以下为可选字段（有默认值）
    sortino_ratio: float = 0.0
    calmar_ratio: float = 0.0
    equity_curve: List[dict] = field(default_factory=list)
    trades: List[Trade] = field(default_factory=list)
    symbols: List[str] = field(default_factory=list)
    logs: List[BacktestLogEntry] = field(default_factory=list)
    analyzers_detail: Optional[Dict[str, Any]] = None

