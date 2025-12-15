# PyQuantAlpha 系统架构图

## 顶层架构概览 (System Overview)

PyQuantAlpha 是一个基于 FastAPI 的 AI 驱动量化回测平台。核心架构分为 **前端交互层**、**API 服务层**、**AI 核心层**、**回测引擎层** 和 **数据服务层**。

```mermaid
graph TD
    %% 样式定义
    classDef front fill:#e1f5fe,stroke:#01579b,stroke-width:2px;
    classDef api fill:#fff3e0,stroke:#ff6f00,stroke-width:2px;
    classDef ai fill:#f3e5f5,stroke:#7b1fa2,stroke-width:2px;
    classDef backtest fill:#e8f5e9,stroke:#2e7d32,stroke-width:2px;
    classDef data fill:#eceff1,stroke:#455a64,stroke-width:2px;

    %% 前端层
    subgraph Frontend [前端交互层]
        UI["Web UI (HTML/CSS)"]:::front
        JS["应用逻辑 (app.js / api.js)"]:::front
    end

    %% API 层
    subgraph API [API 服务层]
        FastAPI["FastAPI 主程序"]:::api
        Route_Strat["策略路由 (Strategy Router)"]:::api
        Route_Klines["K线路由 (Klines Router)"]:::api
        SSE["SSE 实时流"]:::api
    end

    %% AI 核心
    subgraph AICore [AI 核心模块]
        Factory["LLM 工厂"]:::ai
        Client["LLM 客户端 (DeepSeek/OpenAI)"]:::ai
        Prompt["Prompt 模板"]:::ai
        Validator["代码校验器 (AST)"]:::ai
    end

    %% 回测引擎
    subgraph Backtest [回测引擎模块]
        Manager["回测管理器 (异步)"]:::backtest
        Engine["回测引擎 (核心)"]:::backtest
        Analyzer["分析器 (指标)"]:::backtest
        Logger["回测日志"]:::backtest
        Models["数据模型 (订单/交易)"]:::backtest
    end

    %% 数据层
    subgraph Data [数据服务层]
        Binance["Binance 客户端"]:::data
        Bar["K线数据模型"]:::data
    end

    %% 关系流向
    UI -->|用户操作| JS
    JS -->|REST API| FastAPI
    JS -->|EventStream| SSE

    FastAPI --> Route_Strat
    FastAPI --> Route_Klines

    %% 策略生成流
    Route_Strat -->|创建| Factory
    Factory -->|返回| Client
    Client -->|使用| Prompt
    Route_Strat -->|校验代码| Validator

    %% 回测流
    Route_Strat -->|启动任务| Manager
    Manager -->|事件流| SSE
    Manager -->|运行| Engine
    Engine -->|记录| Logger
    Engine -->|计算| Analyzer
    Engine -->|使用| Models

    %% 数据流
    Route_Klines --> Binance
    Engine -->|获取历史数据| Binance
    Binance -->|返回| Bar
```

---

## 核心交互流程 (Sequence Flows)

### 1. 策略生成流程 (AI Strategy Generation)

```mermaid
sequenceDiagram
    participant User as 用户
    participant API as API (策略路由)
    participant LLM as LLM 客户端
    participant Val as 校验器

    User->>API: POST /chat (prompt="双均线策略")
    API->>LLM: unified_chat(prompt)
    LLM-->>API: LLMResponse (JSON)
    
    alt is_strategy? (是策略?)
        API->>Val: validate_strategy_code(code)
        Val-->>API: (is_valid, msg)
    end

    API-->>User: ChatResponse (代码 + 解读)
```

### 2. 回测执行流程 (Backtest Execution)

```mermaid
sequenceDiagram
    participant User as 用户
    participant API as API
    participant Mgr as 回测管理器
    participant Eng as 回测引擎
    participant Bin as Binance 客户端

    User->>API: POST /backtest/run (code, symbol, days)
    API->>Val: 校验代码安全
    API->>Bin: get_historical_klines()
    Bin-->>API: K线数据
    API->>Mgr: start_backtest(code, data)
    Mgr-->>API: task_id
    API-->>User: {task_id}

    par Async Execution (异步执行)
        Mgr->>Eng: engine.run()
        loop Every Bar (每根 K 线)
            Eng->>Eng: on_bar()
            Eng->>Eng: _match_orders()
            Eng->>Mgr: Callback(progress)
        end
        Eng-->>Mgr: BacktestResult
    and SSE Stream (SSE 实时流)
        User->>API: GET /backtest/stream/{task_id}
        API->>Mgr: stream_events()
        Mgr-->>User: event: progress
        Mgr-->>User: event: result
    end
```

---

## 模块职责说明

### `src.ai`
负责与大模型交互，生成和解释策略代码。
- **Factory**: 工厂模式创建 LLM 客户端。
- **Validator**: 基于 AST 的静态代码分析，防止恶意代码注入。
- **Response**: 统一的 `LLMResponse` 数据结构。

### `src.backtest`
核心回测逻辑。
- **Manager**: 异步任务管理器，处理多任务并发和 SSE 消息推送。
- **Engine**: 纯 Python 实现的事件驱动回测引擎。
- **Logger**: 结构化日志记录器。

### `src.data`
数据获取与适配。
- **BinanceClient**: 封装 Binance REST API，支持链式调用和自动分页。

### `src.api`
对外 HTTP 接口。
- **FastAPI**: 提供 RESTful 接口和 SSE 流。
