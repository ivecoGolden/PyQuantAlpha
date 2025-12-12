# Step 6: 自研回测引擎 (Backtest Engine) 实施详情

> **目标**: 实现一个轻量级、事件驱动的回测引擎，用于在本地验证 AI 生成的策略代码。

---

## 1. 核心设计理念

- **事件驱动**: 模拟真实交易流，逐根 K 线 (Bar) 推送，避免 "未来函数" 偷看数据。
- **沙箱隔离**: 策略代码在受限环境中运行，通过注入的 Context 对象与引擎交互。
- **可扩展**: 支持手续费、滑点、多空双向交易。
- **纯 Python**: 不依赖复杂第三方回测框架（如 Backtrader），保持轻量和可控。

---

## 2. 模块结构设计

```
src/backtest/
├── __init__.py
├── models.py        # 数据模型 (Order, Trade, Position)
├── engine.py        # 回测引擎核心 (BacktestEngine)
├── analyzer.py      # 绩效分析 (BacktestAnalyzer)
└── exceptions.py    # 回测相关异常
```

---

## 3. 详细类设计

### 3.1 数据模型 (`src/backtest/models.py`)

```python
from enum import Enum
from dataclasses import dataclass, field
from typing import Optional

class OrderSide(Enum):
    BUY = "BUY"
    SELL = "SELL"

class OrderStatus(Enum):
    PENDING = "PENDING"
    FILLED = "FILLED"
    CANCELLED = "CANCELLED"
    REJECTED = "REJECTED"

class OrderType(Enum):
    MARKET = "MARKET"  # 市价单
    LIMIT = "LIMIT"    # 限价单 (可选实现)

@dataclass
class Order:
    id: str
    symbol: str
    side: OrderSide
    order_type: OrderType
    quantity: float
    price: float = None       # 限价单价格
    created_at: int = 0
    status: OrderStatus = OrderStatus.PENDING
    filled_avg_price: float = 0
    filled_quantity: float = 0
    fee: float = 0
    error_msg: str = ""

@dataclass
class Trade:
    id: str
    order_id: str
    symbol: str
    side: OrderSide
    price: float
    quantity: float
    fee: float
    timestamp: int

@dataclass
class Position:
    symbol: str
    quantity: float = 0       # 正数多头，负数空头
    avg_price: float = 0      # 持仓均价
    
    @property
    def market_value(self) -> float:
        """市值 (由外部更新当前价格计算)"""
        # 注意：需要引擎传入当前价格才能计算准确市值，
        # 这里仅存储基础数据，盈亏计算由 Analyzer 处理
        pass
```

### 3.2 回测配置与引擎 (`src/backtest/engine.py`)

```python
@dataclass
class BacktestConfig:
    initial_capital: float = 100000.0  # 初始资金
    commission_rate: float = 0.001     # 手续费率 (0.1%)
    slippage: float = 0.0005           # 滑点 (0.05%)
    # risk_free_rate: float = 0.02     # 无风险利率 (用于夏普比率)

class BacktestEngine:
    def __init__(self, config: BacktestConfig):
        self.config = config
        self.cash = config.initial_capital
        self.positions: Dict[str, Position] = {}
        self.orders: List[Order] = []
        self.trades: List[Trade] = []
        self.equity_curve: List[dict] = []  # {timestamp, equity}
        
        # 内部状态
        self._current_bar: Optional[Bar] = None
        self._strategy_instance = None
    
    def load_strategy(self, strategy_code: str):
        """加载策略代码并实例化"""
        # 使用 src.ai.validator.execute_strategy_code 获取实例
        # 注入 API 方法 (order, close, etc.)
        pass

    def run(self, data: List[Bar]):
        """运行回测主循环"""
        # 1. 调用 strategy.init()
        # 2. 遍历数据
        for bar in data:
            self._current_bar = bar
            
            # 2.1 撮合待处理订单 (Market/Limit)
            self._match_orders(bar)
            
            # 2.2 更新持仓市值与账户净值
            self._update_equity(bar)
            
            # 2.3 执行策略 on_bar
            self._strategy_instance.on_bar(bar)
            
    def _match_orders(self, bar: Bar):
        """订单撮合逻辑"""
        # 简单回测假设：
        # - 市价单以当前 Close 价格成交 (加减滑点)
        # - 资金不足/持仓不足则 REJECT
        pass
    
    # === 注入给策略的方法 ===
    def _api_order(self, symbol, side, quantity, price=None):
        """策略调用的下单接口"""
        pass
    
    def _api_close(self, symbol):
        """策略调用的平仓接口"""
        pass
```

### 3.3 绩效分析 (`src/backtest/analyzer.py`)

```python
@dataclass
class PerformanceMetrics:
    total_return: float      # 总收益率
    annualized_return: float # 年化收益率
    max_drawdown: float      # 最大回撤
    sharpe_ratio: float      # 夏普比率
    win_rate: float          # 胜率
    profit_factor: float     # 盈亏比
    total_trades: int        # 总交易数

class BacktestAnalyzer:
    @staticmethod
    def analyze(
        initial_capital: float, 
        equity_curve: List[dict], 
        trades: List[Trade]
    ) -> PerformanceMetrics:
        """计算各项指标"""
        pass
```

---

## 4. 实施计划

| 步骤 | 任务 | 描述 |
|-----|-----|------|
| 1 | 数据结构 | 创建 `models.py` 定义 Order/Trade/Position |
| 2 | 分析器 | 创建 `analyzer.py` 实现核心指标计算逻辑 |
| 3 | 引擎核心 | 创建 `engine.py` 实现订单撮合、资金管理循环 |
| 4 | 策略集成 | 对接 `src.ai.validator` 的执行器，实现上下文注入 |
| 5 | 单元测试 | 针对撮合逻辑、资金计算、指标准确性编写测试 |
| 6 | API 对接 | 将 API 中的 Mock 逻辑替换为真实 `BacktestEngine` 调用 |

---

## 5. 验证计划

1.  **单元测试**:
    *   `test_backtest/test_models.py`: 基础模型测试
    *   `test_backtest/test_engine.py`:
        *   测试资金扣除是否正确
        *   测试买入后持仓增加
        *   测试卖出后盈亏计算
        *   测试滑点和手续费的影响
    *   `test_backtest/test_analyzer.py`: 使用已知数据验证夏普率、回撤计算准确性

2.  **集成测试**:
    *   使用 Mock 数据 (正弦波) 运行简单均线策略，验证是否产生预期交易。

3.  **主要风险点**:
    *   **未来数据泄露**: 确保策略只能看到当前 Bar。
    *   **计算精度**: 浮点数计算误差 (考虑使用 Decimal，但为了性能可能仍用 float，需注意 epsilon)。
    *   **AI 代码错误**: 策略代码抛出异常时引擎不应崩溃，应记录错误并停止回测。
