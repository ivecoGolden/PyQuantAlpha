# Phase 2 开发路线图：核心回测能力升级

## 1. 目标概述 (Overview)

Phase 2 的核心目标是将 PyQuantAlpha 从一个 "AI 演示工具" 升级为具备 "实战验证能力" 的量化回测引擎。
**优先级调整**：根据讨论，我们将优先完善 **日志与可视化** 能力，以便于更好地观测策略行为；随后建立 **高级订单系统** 弥补风控缺失；最后进行底层架构升级以支持 **多资产模式**。

## 2. 核心功能规划 (Core Features)

### 2.1 [P0] 增强型日志与可视化 (Logging & Visualization)
**参考**：Backtrader 的 `Writer` 和 `Observer` 机制及 `notify_order` 回调。
**现状**：仅记录净值曲线，无法知道具体的成交时间、价格和费用。
**目标**：实现“透明化回测”，所有动作可追溯，并在前端图表上标记。

- **[T1] 策略回调钩子 (Strategy Hooks)**
    - 实现 `notify_order(order)`：当订单状态改变（提交、成交、取消）时触发。
    - 实现 `notify_trade(trade)`：当一笔完整的交易（开仓+平仓）结束时触发。
    - 允许策略在这些钩子中自定义 `print` 或 `log` 行为。
- **[T2] 结构化日志增强**
    - 改造 `BacktestLogger`，增加 `orders` 和 `trades` 的详细流水记录。
    - 日志字段对齐 Backtrader：`ref`, `type`, `size`, `price`, `comm`。
- **[T3] 可视化数据适配**
    - 在 API 返回的 JSON 中包含 `markers` 数组（买卖点）。
    - 前端 Highcharts 绘制 Buy(绿色三角形) 和 Sell(红色三角形) 标记。

### 2.2 [P1] 交易核心重构 (Core Trading Engine)
**参考**：Backtrader 的 `Broker` 抽象与完整订单生命周期。
**现状**：撮合逻辑耦合在 Engine 中，仅支持市价/限价，状态简单。
**目标**：解耦交易执行层，支持复杂订单与更真实的资金管理。

- **[T4] 引入 Broker 抽象层**
    - **架构升级**：从 `Engine` 中剥离交易逻辑，建立 `BacktestBroker` 类。
    - **职责**：接管资金 (`cash`, `value`)、持仓 (`positions`) 管理及订单撮合 (`_match_orders`)。
    - **意义**：为未来对接实盘交易（Live Trading）预留接口，实现逻辑解耦。
- **[T5] 完善订单生命周期**
    - **状态机升级**：引入完整状态 `Submitted` -> `Accepted` -> `Partial` -> `Completed` / `Canceled` / `Rejected` (资金不足)。
    - **风控订单**：实现 `STOP` (止损) 和 `STOP_LIMIT` (止损限价) 订单。
    - **触发机制**：借鉴 BT，严格区分 "Triggered" (触发) 与 "Executed" (成交)。
- **[T6] 资金管理预留 (Sizer)**
    - 在 `Order` 接口中预留自动计算数量的逻辑（如 `size=None` 时按资金百分比下单），为未来引入 `Sizer` 模块做准备。

### 2.3 [P2] 多资产回测引擎 (Multi-Asset Core)
**参考**：Backtrader 的 `Cerebro` 数据对齐与 `Lines` 索引。
**现状**：单列表 `List[Bar]`。
**目标**：支持多币种对冲/轮动策略。

- **[T6] 数据对齐 (Data Alignment)**
    - **实现方案**:  **并集时间轴 + 前值填充 (Forward Fill)**。主循环遍历所有数据源的时间戳并集。若某资产当前时间点无数据，自动填充上一个有效周期的 Bar（标记 `staleness=True`）。
    - 策略 API 变更：采用显式字典 `self.datas["BTC"]` 获取数据对象。
- **[T7] 引擎重构 & API 变更**
    - **实现方案**: **Breaking Change 设计**。
    - `on_bar(self, bars)` 入参改为 `Dict[str, Bar]`。
    - 策略代码必须显式调用 `bars["BTC"].close`，移除单数 `bar` 参数以消除歧义。
    - 重写 `Engine.run` 循环，支持处理上述字典结构。
    - 仓位管理升级为 `Dict[symbol, Position]`。

---

## 3. 实施阶段 (Implementation Phasing)

1.  **Phase 2.1 (Logging)**: 不破坏现有引擎结构，仅增强 `Observer` 和 `Callback`。
2.  **Phase 2.2 (Core Trading)**: 提取 `BacktestBroker`，实现新的订单状态机与止损单逻辑。
3.  **Phase 2.3 (Multi-Asset)**: 较大的底层重构，需确保前两步的单元测试覆盖充分，以防止回滚。

---

## 附录：关键技术决策说明 (Technical Decisions Appendix)

### D1: 数据对齐策略 (Data Alignment Strategy)
> **决策**：采用 **并集时间轴 (Union Timestamps) + 前值填充 (Forward Fill)** 机制。
> **背景**：在多资产模式下，不同交易对（如 BTC 和 ETH，或不同交易所数据）的时间戳可能无法完全对齐（例如某分钟没有成交）。
> **解释**：
> 1.  引擎会先计算所有输入数据源的时间戳并集，生成一个完整的主时间轴。
> 2.  按时间顺序推进时，如果某个币种在当前时间点缺失数据，系统会自动使用其 **上一根有效 K 线** 的数据进行填充（即认为价格维持不变）。
> 3.  这模拟了真实交易环境：即使某个市场暂时沉寂，你依然可以根据其他市场的变动来操作该市场的持仓。

### D2: API 兼容性 (API Compatibility)
> **决策**：采用 **不兼容升级 (Breaking Change)**，重构 `on_bar` 接口。
> **背景**：现有的 `on_bar(bar)` 仅支持单资产，若要支持多资产，存在"通过代理对象维持兼容"和"直接改为字典"两种路线。
> **解释**：
> 1.  我们选择 **直接改为字典 `on_bar(bars: Dict[str, Bar])`**。
> 2.  虽然这会破坏旧策略的兼容性（旧策略需修改代码），但它消除了代码层面的歧义（Ambiguity）。
> 3.  在开发阶段明确数据结构优于通过 Magic Methods 隐藏复杂性，有利于长期维护和 AI 生成代码的准确性。

## 整体结构图

```mermaid
graph LR
    %% 样式定义 - 使用高对比度颜色搭配白色文字
    classDef front fill:#1976D2,stroke:#0D47A1,stroke-width:2px,color:white;
    classDef api fill:#F57C00,stroke:#E65100,stroke-width:2px,color:white;
    classDef ai fill:#7B1FA2,stroke:#4A148C,stroke-width:2px,color:white;
    classDef backtest fill:#388E3C,stroke:#1B5E20,stroke-width:2px,color:white;
    classDef data fill:#546E7A,stroke:#263238,stroke-width:2px,color:white;

    %% 前端层 (左侧入口)
    subgraph Frontend [前端交互层]
        direction TB
        UI["网页前端 (HTML/CSS)"]:::front
        JS["应用逻辑 (Vue/JS)"]:::front
        UI -->|用户操作| JS
    end

    %% API 层 (中间网关)
    subgraph API [API 服务层]
        direction TB
        FastAPI["FastAPI 主程序"]:::api
        Route_Strat["策略接口路由"]:::api
        Route_Klines["行情接口路由"]:::api
        SSE["实时消息流 (SSE)"]:::api
        
        FastAPI --> Route_Strat
        FastAPI --> Route_Klines
    end

    %% 核心业务模块 (右侧并行)
    subgraph Core [核心业务模块]
        direction TB
        
        %% AI 核心
        subgraph AICore [AI 核心模块]
            direction TB
            Factory["LLM 工厂类"]:::ai
            Client["AI 客户端"]:::ai
            Validator["安全校验器"]:::ai
            
            Factory -->Client
        end

        %% 回测引擎
        subgraph Backtest [回测引擎模块]
            direction TB
            Manager["回测管理器 (异步)"]:::backtest
            Engine["回测核心引擎"]:::backtest
            Logger["回测日志"]:::backtest
            
            Manager -->|启动| Engine
            Engine --> Logger
        end
    end

    %% 数据层 (底层支撑)
    subgraph Data [数据服务层]
        Binance["交易所客户端"]:::data
        Bar["K线数据"]:::data
        Binance -.-> Bar
    end

    %% 跨层连接
    JS -->|REST API| FastAPI
    JS -->|EventStream| SSE

    %% 路由分发
    Route_Strat -->|创建| Factory
    Route_Strat -->|校验| Validator
    Route_Strat -->|启动任务| Manager
    
    Route_Klines --> Binance
    
    %% 流程连接
    Client -->|返回代码| Validator
    Manager -->|推送事件| SSE
    Engine -->|请求数据| Binance

    %% 布局调整
    Frontend --> API
    API --> Core
    Core --> Data
```