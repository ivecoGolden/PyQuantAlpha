# Phase 2.2: 交易核心重构 (Broker & Orders)

## 1. 目标 (Goal)
本阶段的目标是重构交易核心，将资金管理和订单撮合逻辑从 `Engine` 中剥离出来，建立独立的 `Broker` 抽象。同时，引入完善的订单生命周期管理和高级订单类型（止损单），为更复杂的策略（如 ATR 止损、移动止盈）提供支持。

## 2. 核心任务分解 (Tasks Breakdown)

### 2.1 [T4] Broker 抽象层实现 (Broker Abstraction)
**目标**：解耦 `Engine` 与 交易执行逻辑。`Engine` 只负责时间推进和策略驱动，`Broker` 负责管钱、管仓、管交易。

- **创建 `src/backtest/broker.py`**
    - **BacktestBroker 类**
        - **属性**:
            - `cash`: 当前可用现金
            - `positions`: `Dict[symbol, Position]` 持仓信息
            - `orders`: `List[Order]` 所有订单历史
            - `active_orders`: `List[Order]` 当前挂单
            - `commission`: 手续费率 (BaseCommission)
            - `slippage`: 滑点模型 (BaseSlippage)
        - **方法**:
            - `get_cash()`, `get_value()`, `get_position(symbol)`
            - `submit_order(order)`: 接收新订单，进行预检（资金/持仓检查），转入 `SUBMITTED` 状态。
            - `cancel_order(order)`: 取消挂单。
            - `process_orders(bar)`: **核心撮合逻辑**。在每个 Bar 到来时被 Engine 调用，检查所有挂单是否成交。

### 2.2 [T5] 订单生命周期与类型升级 (Order Lifecycle & Types)
**目标**：支持标准化的订单状态机和高级订单类型。

- **升级 `src/backtest/models.py`**
    - **OrderType 枚举扩展**:
        - `MARKET`: 市价单 (现有)
        - `LIMIT`: 限价单 (现有)
        - `STOP`: 止损单 (新增 - 触价即市价)
        - `STOP_LIMIT`: 止损限价单 (新增 - 触价即限价)
    - **OrderStatus 枚举扩展**:
        - `CREATED`: 创建但未提交
        - `SUBMITTED`: 已提交给 Broker
        - `ACCEPTED`: Broker 已受理（预检通过）
        - `PARTIAL`: 部分成交 (预留，暂不实现复杂部分成交)
        - `FILLED`: 全部成交
        - `CANCELED`: 已取消
        - `REJECTED`: 拒单 (资金不足/无效参数)
        - `EXPIRED`: 过期 (TTL/Day order)
    - **Order 类扩展**:
        - `executed_price`: 成交均价
        - `executed_size`: 成交数量
        - `trigger_price`: 触发价格 (针对 STOP 单)

### 2.3 [T5.1] 撮合逻辑实现 (Matching Logic)
**目标**：在 `Broker.process_orders` 中实现不同类型订单的撮合规则。

- **撮合规则表**:
    - **Market**: 下一根 Bar 开盘价 (或 Close，取决于配置) 成交。
    - **Limit (Buy)**: 当 `Low <= limit_price` 时成交。成交价通常为 `limit_price` 或 `Open` (如果 Open 优于 limit)。
    - **Limit (Sell)**: 当 `High >= limit_price` 时成交。
    - **Stop (Buy)**: 当 `High >= trigger_price` 时触发，转为市价单在次日/当日成交。
    - **Stop (Sell)**: 当 `Low <= trigger_price` 时触发，转为市价单。

### 2.4 [T6] 仓位管理预留 (Sizer Foundation)
**目标**：支持简单的自动仓位计算。

- **Sizer 概念引入**:
    - 在 Strategy 中增加 `setsizer(sizer)` 方法。
    - **FixedSize**: 每次固定买 N 个。
    - **PercentSizer**: 每次买账户权益的 X%。
    - 当 `order(size=None)` 时，调用 `sizer.getsizing()` 计算下单量。

## 3. 实现指引 (Implementation Steps)

### Step 1: 模型升级 (`models.py`)
1.  修改 `OrderType` 和 `OrderStatus` 枚举。
2.  更新 `Order` 类字段，添加 `trigger_price`, `parent_id` (用于 OCO 订单关联，暂只留字段)。

### Step 2: 实现 Broker (`broker.py`)
1.  将 `Engine` 中的 `cash`, `positions`, `_match_orders` 逻辑迁移到 `BacktestBroker`。
2.  重写 `process_orders` 以支持 `STOP` 单的触发逻辑。
    - *Flag 标记*: Stop 单需要维护一个 `triggered` 状态，触发后下一 tick 执行。

### Step 3: 改造 Engine (`engine.py`)
1.  Engine 初始化时实例化 `BacktestBroker`。
2.  `Engine.run` 中，在循环开始处调用 `broker.process_orders(bar)`。
3.  代理 Strategy 的 `buy/sell` 请求，转发给 `broker.submit_order`。

### Step 4: 策略适配 (`strategy.py`)
1.  确保 Strategy 基类的 `buy`, `sell`, `close` 方法兼容新的 Order 参数 (如 `exectype`, `trigger`)。
2.  更新 `notify_order` 以处理新的状态变化。

## 4. 验证计划 (Verification)

1.  **Stop Order 测试**:
    - 在上涨趋势中下 STOP BUY 单，验证是否在突破 `trigger_price` 后才成交。
    - 在下跌趋势中下 STOP SELL 单 (止损)，验证是否触价成交。
2.  **资金风控测试**:
    - 满仓后继续下单，验证是否返回 `REJECTED` 状态。
3.  **回归测试**:
    - 运行之前的 `SIMPLE_STRATEGY`，确保市价单逻辑依然正确，净值计算无误。
