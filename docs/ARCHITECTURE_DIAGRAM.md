# PyQuantAlpha 系统架构图

> **更新于 Phase 3 完成后 (2025-12-27)**

## 顶层架构概览

PyQuantAlpha 是一个基于 FastAPI 的 AI 驱动量化回测平台。核心架构分为 **前端交互层**、**API 服务层**、**AI 核心层**、**回测引擎层**、**数据服务层** 和 **存储层**。

```mermaid
graph LR
    %% 样式定义
    classDef front fill:#1976D2,stroke:#0D47A1,stroke-width:2px,color:white;
    classDef api fill:#F57C00,stroke:#E65100,stroke-width:2px,color:white;
    classDef ai fill:#7B1FA2,stroke:#4A148C,stroke-width:2px,color:white;
    classDef backtest fill:#388E3C,stroke:#1B5E20,stroke-width:2px,color:white;
    classDef data fill:#546E7A,stroke:#263238,stroke-width:2px,color:white;
    classDef storage fill:#5D4037,stroke:#3E2723,stroke-width:2px,color:white;
    classDef indicator fill:#00796B,stroke:#004D40,stroke-width:2px,color:white;

    %% 前端层
    subgraph Frontend ["前端交互层"]
        direction TB
        UI["网页前端 (HTML/CSS)"]:::front
        JS["应用逻辑 (JS)"]:::front
        Chart["TradingView 图表"]:::front
        UI --> JS
        JS --> Chart
    end

    %% API 层
    subgraph API ["API 服务层"]
        direction TB
        FastAPI["FastAPI 主程序"]:::api
        Route_Strat["策略接口"]:::api
        Route_Klines["行情接口"]:::api
        Route_Explain["解释接口"]:::api
        SSE["SSE 实时推送"]:::api
        FastAPI --> Route_Strat
        FastAPI --> Route_Klines
        FastAPI --> Route_Explain
    end

    %% AI 核心
    subgraph AICore ["AI 核心模块"]
        direction TB
        Factory["LLM 工厂"]:::ai
        Client["AI 客户端"]:::ai
        Validator["AST 安全校验"]:::ai
        Prompt["Prompt 模板"]:::ai
        Factory --> Client
        Client --> Prompt
    end

    %% 回测引擎
    subgraph Backtest ["回测引擎"]
        direction TB
        Manager["任务管理器"]:::backtest
        Engine["核心引擎"]:::backtest
        Broker["经纪商模拟"]:::backtest
        Sizer["仓位管理"]:::backtest
        Slippage["滑点模型"]:::backtest
        Commission["手续费模型"]:::backtest
        Analyzer["业绩分析器"]:::backtest
        Logger["回测日志"]:::backtest
        
        Manager --> Engine
        Engine --> Broker
        Broker --> Sizer
        Broker --> Slippage
        Broker --> Commission
        Engine --> Analyzer
        Engine --> Logger
    end

    %% 技术指标
    subgraph Indicators ["技术指标库"]
        direction TB
        MA["均线 (SMA/EMA)"]:::indicator
        OSC["振荡器 (RSI/Stoch)"]:::indicator
        VOL["波动率 (ATR/BB)"]:::indicator
        ADV["高级 (ADX/Ichimoku)"]:::indicator
    end

    %% 数据服务层
    subgraph Data ["数据服务层"]
        direction TB
        Repo["数据仓库"]:::data
        BinanceSpot["现货 API"]:::data
        BinanceFutures["合约 API"]:::data
        Resampler["多周期重采样"]:::data
        
        Repo --> BinanceSpot
        Repo --> BinanceFutures
        Repo --> Resampler
    end

    %% 存储层
    subgraph Storage ["持久化存储层"]
        direction TB
        SQLite[("SQLite")]:::storage
        ORM["SQLAlchemy ORM"]:::storage
        Models["数据模型"]:::storage
        ORM --> SQLite
        Models --> ORM
    end

    %% 消息模块
    subgraph Messages ["消息模块"]
        ErrorMsg["错误消息"]:::api
    end

    %% 跨层连接
    JS -->|REST API| FastAPI
    JS -->|EventStream| SSE

    Route_Strat --> Factory
    Route_Strat --> Validator
    Route_Strat --> Manager
    Route_Explain --> Client
    Route_Klines --> Repo

    Engine --> Indicators
    Engine --> Repo
    Repo --> ORM

    Manager -->|推送事件| SSE

    %% 布局
    Frontend --> API
    API --> AICore
    API --> Backtest
    Backtest --> Data
    Data --> Storage
```

---

## 核心业务流程

### 1. 策略生成流程 (AI Strategy Generation)

```mermaid
sequenceDiagram
    participant User as 用户 (前端)
    participant API as 后端接口
    participant LLM as AI 模型
    participant Val as 安全校验

    User->>API: 发送聊天请求 (如"写个双均线策略")
    API->>LLM: 调用大模型接口 (含 Prompt 模板)
    LLM-->>API: 返回 JSON 格式响应
    
    alt 包含策略代码?
        API->>Val: AST 静态分析 + 动态白名单校验
        Val-->>API: 返回校验结果 (通过/拦截)
    end

    API-->>User: 返回策略代码
    
    Note over User,API: 异步解释流程
    User->>API: 请求策略解释 (/api/explain)
    API->>LLM: 调用解释专用 Prompt
    LLM-->>API: 返回策略解读
    API-->>User: 返回解释内容
```

### 2. 回测执行流程 (Backtest Execution)

```mermaid
sequenceDiagram
    participant User as 用户 (前端)
    participant API as 后端接口
    participant Val as 安全校验
    participant Repo as 数据仓库
    participant DB as SQLite
    participant Mgr as 回测管理器
    participant Eng as 回测引擎
    participant Broker as 经纪商

    User->>API: 提交回测请求 (代码, 币种, 天数)
    API->>Val: 二次校验代码安全
    
    API->>Repo: 请求历史数据
    Repo->>DB: 查询本地缓存
    
    alt 缓存缺失或过期
        Repo->>BinanceAPI: 拉取远程数据
        BinanceAPI-->>Repo: 返回 K 线数据
        Repo->>DB: 持久化存储
    end
    
    Repo-->>API: 返回 K 线列表
    API->>Mgr: 创建异步回测任务
    Mgr-->>API: 返回任务 ID
    API-->>User: 响应任务 ID

    par 异步执行
        Mgr->>Eng: 启动引擎运行
        Eng->>Broker: 初始化 (Sizer/Slippage/Commission)
        loop 每一根 K 线
            Eng->>Eng: 策略逻辑 (on_bar)
            Eng->>Broker: 订单处理
            Broker->>Broker: 滑点 + 手续费计算
            Broker->>Broker: 订单撮合
            Eng->>Mgr: 上报进度
        end
        Eng->>Analyzer: 计算业绩指标
        Analyzer-->>Eng: Sharpe/MaxDD/Returns
        Eng-->>Mgr: 返回回测报告
    and 实时推送
        User->>API: 监听 SSE 消息流
        API->>Mgr: 订阅任务事件
        Mgr-->>User: 推送进度 (Progress)
        Mgr-->>User: 推送结果 (Result)
    end
```

---

## 模块职责说明

### `src.ai` (AI 核心)

负责与大模型交互，智能生成和解释量化策略。

| 组件 | 文件 | 职责 |
|------|------|------|
| 工厂类 | `factory.py` | 创建不同的 LLM 客户端实例 |
| 基类 | `base.py` | 定义 LLM 客户端抽象接口 |
| DeepSeek | `deepseek.py` | DeepSeek API 实现 |
| OpenAI | `openai_client.py` | OpenAI API 实现 |
| Prompt | `prompt.py` | 策略生成/解释的系统提示词模板 |
| 校验器 | `validator.py` (via backtest) | AST 静态分析 + 动态白名单 |

---

### `src.backtest` (回测系统)

执行量化策略的核心模块，包含完整的交易仿真系统。

| 组件 | 文件/目录 | 职责 |
|------|-----------|------|
| 管理器 | `manager.py` | 异步任务调度，管理并发回测 |
| 核心引擎 | `engine.py` | 事件驱动回测，协调各模块 |
| 经纪商 | `broker.py` | 订单撮合、持仓管理、高级订单 (Bracket/OCO/TrailingStop) |
| 仓位管理 | `sizers/` | FixedSize / PercentSize / AllIn / RiskSize |
| 滑点模型 | `slippage/` | 固定滑点 / 百分比滑点 |
| 手续费 | `commission.py` | 手续费计算模型 |
| 分析器 | `analyzers/` | Sharpe / Sortino / MaxDrawdown / Returns / Trades |
| 数据 Feed | `feed.py` | 多时间周期数据对齐 |
| 加载器 | `loader.py` | 策略代码安全加载 |
| 日志 | `logger.py` | 交易流水记录 |
| 模型 | `models.py` | Order / Position / Bar 等数据结构 |

---

### `src.data` (数据服务)

负责市场数据的获取、缓存与清洗。

| 组件 | 文件 | 职责 |
|------|------|------|
| 数据仓库 | `repository.py` | 透明同步层，统一数据访问入口 |
| 现货客户端 | `binance.py` | Binance 现货 API 封装 |
| 合约客户端 | `binance_futures.py` | Binance Futures API (资金费率/多空比) |
| 重采样器 | `resampler.py` | K 线多周期重采样 |
| 数据模型 | `models.py` | Bar / Tick 等数据结构 |
| 抽象基类 | `base.py` | 数据源抽象接口 |

---

### `src.database` (持久化存储)

基于 SQLAlchemy 的本地数据持久化层。

| 组件 | 文件 | 职责 |
|------|------|------|
| 数据库管理 | `database.py` | SQLite 连接池、WAL 模式配置 |
| ORM 模型 | `models.py` | Candlestick / FundingRate / MarketSentiment |

---

### `src.indicators` (技术指标)

完整的技术分析指标库。

| 组件 | 文件 | 包含指标 |
|------|------|----------|
| 基类 | `base.py` | BaseIndicator 抽象类 |
| 均线类 | `ma.py` | SMA, EMA |
| 振荡器 | `oscillator.py` | RSI, Stochastic, CCI, Williams %R |
| 波动率 | `volatility.py` | ATR, Bollinger Bands |
| 高级指标 | `advanced.py` | MACD, ADX, Ichimoku, OBV |

---

### `src.messages` (消息模块)

统一的消息管理系统。

| 组件 | 文件 | 职责 |
|------|------|------|
| 错误消息 | `errorMessage.py` | 多交易所错误码映射、链式消息构建 |

---

### `src.api` (接口层)

对外提供 HTTP 服务。

| 组件 | 文件/目录 | 职责 |
|------|-----------|------|
| 主程序 | `main.py` | FastAPI 应用入口 |
| 路由 | `routes/` | 策略 / 行情 / 解释 / SSE 接口 |
| 静态资源 | `static/` | 前端 HTML/CSS/JS |
| 数据模式 | `schemas/` | Pydantic 请求/响应模型 |

---

## 数据流架构

```mermaid
graph TB
    subgraph External ["外部数据源"]
        BinanceSpot["Binance 现货 API"]
        BinanceFutures["Binance 合约 API"]
    end

    subgraph Repository ["数据仓库层"]
        Repo["MarketDataRepository"]
        Cache["缓存检查"]
        Sync["透明同步"]
    end

    subgraph Storage ["存储层"]
        SQLite[("SQLite\nWAL 模式")]
        Candlestick["K 线表"]
        FundingRate["资金费率表"]
        Sentiment["市场情绪表"]
    end

    subgraph Consumer ["数据消费者"]
        Engine["回测引擎"]
        Indicators["指标计算"]
        Resampler["重采样器"]
    end

    BinanceSpot --> Sync
    BinanceFutures --> Sync
    
    Repo --> Cache
    Cache -->|命中| SQLite
    Cache -->|未命中| Sync
    Sync --> SQLite
    
    SQLite --> Candlestick
    SQLite --> FundingRate
    SQLite --> Sentiment
    
    Repo --> Engine
    Repo --> Indicators
    Repo --> Resampler
```

---

## 回测引擎内部架构

```mermaid
graph TB
    subgraph Engine ["回测引擎核心"]
        Core["BacktestEngine"]
        Strategy["用户策略"]
        EventLoop["事件循环"]
    end

    subgraph Broker ["经纪商模块"]
        OrderMgr["订单管理器"]
        PositionMgr["持仓管理器"]
        Matcher["撮合引擎"]
    end

    subgraph Simulation ["仿真模型"]
        Sizer["Sizer\n(仓位计算)"]
        Slippage["Slippage\n(滑点模型)"]
        Commission["Commission\n(手续费)"]
    end

    subgraph Analysis ["业绩分析"]
        SharpeAnalyzer["Sharpe Ratio"]
        DrawdownAnalyzer["Max Drawdown"]
        ReturnsAnalyzer["Returns"]
        TradesAnalyzer["Trade Stats"]
    end

    subgraph OrderTypes ["订单类型"]
        Market["市价单"]
        Limit["限价单"]
        Stop["止损单"]
        Bracket["挂钩订单"]
        OCO["OCO 订单"]
        Trailing["移动止损"]
    end

    Core --> Strategy
    Core --> EventLoop
    Core --> Broker
    
    Strategy --> OrderMgr
    OrderMgr --> Sizer
    OrderMgr --> Matcher
    Matcher --> Slippage
    Matcher --> Commission
    Matcher --> PositionMgr
    
    OrderMgr --> OrderTypes
    
    Core --> Analysis
```

---

## 版本演进

| 阶段 | 主要特性 |
|------|----------|
| Phase 1 | AI 策略生成、基础回测引擎、安全校验 |
| Phase 2 | 多资产回测、高级订单、增强日志、SSE 实时推送 |
| Phase 3 | 数据持久化、衍生品数据、Sizer/Slippage/Commission、分析器集成 |
