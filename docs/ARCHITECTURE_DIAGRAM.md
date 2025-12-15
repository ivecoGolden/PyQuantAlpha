# PyQuantAlpha 系统架构图

## 顶层架构概览

PyQuantAlpha 是一个基于 FastAPI 的 AI 驱动量化回测平台。核心架构分为 **前端交互层**、**API 服务层**、**AI 核心层**、**回测引擎层** 和 **数据服务层**。

```mermaid
graph TD
    %% 样式定义 - 使用高对比度颜色搭配白色文字
    classDef front fill:#1976D2,stroke:#0D47A1,stroke-width:2px,color:white;
    classDef api fill:#F57C00,stroke:#E65100,stroke-width:2px,color:white;
    classDef ai fill:#7B1FA2,stroke:#4A148C,stroke-width:2px,color:white;
    classDef backtest fill:#388E3C,stroke:#1B5E20,stroke-width:2px,color:white;
    classDef data fill:#546E7A,stroke:#263238,stroke-width:2px,color:white;

    %% 前端层
    subgraph Frontend [前端交互层]
        UI["网页前端 (HTML/CSS)"]:::front
        JS["应用逻辑 (Vue/JS)"]:::front
    end

    %% API 层
    subgraph API [API 服务层]
        FastAPI["FastAPI 主程序"]:::api
        Route_Strat["策略接口路由"]:::api
        Route_Klines["行情接口路由"]:::api
        SSE["实时消息流 (SSE)"]:::api
    end

    %% AI 核心
    subgraph AICore [AI 核心模块]
        Factory["LLM 工厂类"]:::ai
        Client["AI 客户端 (DeepSeek/OpenAI)"]:::ai
        Prompt["提示词模板"]:::ai
        Validator["安全校验器 (AST)"]:::ai
    end

    %% 回测引擎
    subgraph Backtest [回测引擎模块]
        Manager["回测任务管理器 (异步)"]:::backtest
        Engine["回测核心引擎"]:::backtest
        Analyzer["绩效分析器"]:::backtest
        Logger["回测日志"]:::backtest
        Models["数据模型 (订单/交易)"]:::backtest
    end

    %% 数据层
    subgraph Data [数据服务层]
        Binance["交易所客户端 (Binance)"]:::data
        Bar["K线数据结构"]:::data
    end

    %% 关系流向
    UI -->|用户操作| JS
    JS -->|REST API 请求| FastAPI
    JS -->|监听事件| SSE

    FastAPI --> Route_Strat
    FastAPI --> Route_Klines

    %% 策略生成流
    Route_Strat -->|创建实例| Factory
    Factory -->|返回| Client
    Client -->|调用| Prompt
    Route_Strat -->|代码安全检查| Validator

    %% 回测流
    Route_Strat -->|提交任务| Manager
    Manager -->|推送进度| SSE
    Manager -->|执行回测| Engine
    Engine -->|记录流水| Logger
    Engine -->|计算指标| Analyzer
    Engine -->|更新状态| Models

    %% 数据流
    Route_Klines --> Binance
    Engine -->|请求历史数据| Binance
    Binance -->|返回数据| Bar
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
    API->>LLM: 调用大模型接口
    LLM-->>API: 返回 JSON 格式响应
    
    alt 包含策略代码?
        API->>Val: 对生成的 Python 代码进行 AST 校验
        Val-->>API: 返回校验结果 (通过/拦截)
    end

    API-->>User: 返回最终结果 (代码 + 解读)
```

### 2. 回测执行流程 (Backtest Execution)

```mermaid
sequenceDiagram
    participant User as 用户 (前端)
    participant API as 后端接口
    participant Mgr as 回测管理器
    participant Eng as 回测引擎
    participant Bin as 数据源

    User->>API: 提交回测请求 (代码, 币种, 天数)
    API->>Val: 二次校验代码安全
    API->>Bin: 拉取历史 K 线数据
    Bin-->>API: 返回 K 线列表
    API->>Mgr: 创建异步回测任务
    Mgr-->>API: 返回 任务ID
    API-->>User: 响应 任务ID

    par 异步执行
        Mgr->>Eng: 启动引擎运行
        loop 每一根 K 线
            Eng->>Eng: 策略逻辑 (on_bar)
            Eng->>Eng: 订单撮合
            Eng->>Mgr: 上报进度 (回调)
        end
        Eng-->>Mgr: 返回回测报告
    and 实时推送
        User->>API: 监听 SSE 消息流
        API->>Mgr: 订阅任务事件
        Mgr-->>User: 推送: 进度条 (Progress)
        Mgr-->>User: 推送: 最终结果 (Result)
    end
```

---

## 模块职责说明

### `src.ai` (AI 核心)
负责与大模型交互，智能生成和解释量化策略。
- **工厂类 (Factory)**: 负责创建不同的大模型客户端（如 DeepSeek, OpenAI）。
- **校验器 (Validator)**: 基于 AST (抽象语法树) 的静态代码分析工具，防止生成的代码包含删除文件等危险操作。
- **响应结构**: 统一封装 AI 返回的数据格式。

### `src.backtest` (回测系统)
执行量化策略的核心模块。
- **管理器 (Manager)**: 异步任务调度中心，负责管理并发的回测任务和消息推送。
- **核心引擎 (Engine)**: 纯 Python 实现的事件驱动回测引擎，模拟交易所撮合逻辑。
- **日志 (Logger)**: 记录详细的交易流水，用于前端图表展示。

### `src.data` (数据服务)
负责市场数据的获取与清洗。
- **客户端 (BinanceClient)**: 封装交易所 API，支持自动分页拉取长周期数据。

### `src.api` (接口层)
对外提供 HTTP 服务。
- **FastAPI**: 高性能 Web 框架，提供 RESTful 接口和 SSE 实时流功能。
