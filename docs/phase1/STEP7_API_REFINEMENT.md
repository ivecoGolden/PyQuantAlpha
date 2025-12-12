# Step 7: API 端点完善 (API Refinement) 实施详情

> **目标**: 升级 API 以支持更丰富的 AI 交互（策略解读）和实时回测体验（SSE流式推送），为前端交互打下基础。

---

## 1. 核心功能设计

### 1.1 AI 策略解读
- **现状**: 仅返回生成的 Python 代码。
- **需求**: 用户看不懂代码，需要自然语言解读（策略逻辑、买卖点、风险提示）。
- **方案**:
    - 优化 Prompt，要求 LLM 输出分为 `[CODE]` 和 `[EXPLANATION]` 两部分。
    - 后端解析提取这两部分，分别返回给前端。

### 1.2 实时回测 (Real-time Backtesting)
- **现状**: 只返回最终结果 (`BacktestResponse`)，前端无法感知进度。
- **需求**: 前端显示进度条、实时净值变化曲线。
- **方案**:
    - **SSE (Server-Sent Events)**: 适合单向实时推送（Server -> Client）。
    - **异步与回调**: `BacktestEngine` 运行在独立线程/协程，并通过回调函数 (`on_progress`) 将状态推送到 SSE 队列。
    - **内存管理**: 暂不引入 Redis/Celery，使用简单的内存 `BacktestManager` 管理运行中的回测任务。

---

## 2. 接口设计

### 2.1 策略生成 (`POST /api/generate`)

**Response Update**:
```python
class GenerateResponse(BaseModel):
    code: str              # 策略代码
    explanation: str       # 策略解读 (Markdown) [新增]
    message: str           # 状态消息
    is_valid: bool         # 是否有效
```

### 2.2 启动回测 (`POST /api/backtest/run`)

**Request**:
```python
class BacktestRunRequest(BaseModel):
    code: str             # 策略代码
    symbol: str = "BTCUSDT"
    interval: str = "1h"
    start_time: int       # 开始时间戳 (ms)
    end_time: int         # 结束时间戳 (ms)
    initial_capital: float = 100000.0
```

**Response**:
```python
{
    "task_id": "uuid-string",  # 任务 ID，用于监听 SSE
    "message": "Backtest started"
}
```

### 2.3 监听进度 (`GET /api/backtest/stream/{task_id}`)

**Protocol**: `text/event-stream`

**Events**:

1.  **progress**: 进度更新
    ```json
    {
        "type": "progress",
        "data": {
            "progress": 45,       // 0-100
            "current_date": "2023-01-01",
            "equity": 105000.0
        }
    }
    ```

2.  **result**: 回测完成
    ```json
    {
        "type": "result",
        "data": { ...BacktestResponse... }
    }
    ```

3.  **error**: 发生错误
    ```json
    {
        "type": "error",
        "data": { "message": "资金不足" }
    }
    ```

---

## 3. 模块修改计划

### 3.1 AI 模块 (`src/ai/`)
1.  修改 `SYSTEM_PROMPT` (`src/ai/prompt.py`): 明确要求输出格式。
2.  修改 `BaseLLMClient._extract_code` (`src/ai/base.py`): 解析代码和解读。

### 3.2 回测引擎 (`src/backtest/engine.py`)
1.  修改 `run` 方法，增加 `on_progress` 回调参数：
    ```python
    def run(self, strategy_code: str, data: List[Bar], on_progress: Callable[[int, int, float], None] = None):
        # ...
        # 在循环中调用 on_progress(current_idx, total_len, current_equity)
    ```

### 3.3 回测管理器 (`src/backtest/manager.py`) [新增]
- 负责管理运行中的回测任务。
- 使用 `asyncio.Queue` 实现消息发布/订阅。

```python
class BacktestManager:
    def __init__(self):
        self.tasks = {} # task_id -> {"queue": asyncio.Queue, "status": "running"}

    async def start_backtest(self, params: BacktestRunRequest) -> str:
        # 创建 task_id
        # 启动异步任务 run_backtest_task(...)
        return task_id
    
    async def stream_events(self, task_id: str):
        # 产生 SSE 生成器
        while True:
            event = await queue.get()
            yield format_sse(event)
```

---

## 4. 验证计划

1.  **AI 生成测试**:
    - Mock AI 返回包含 `[EXPLANATION]` 标记的文本，验证解析逻辑。
2.  **SSE 连接测试**:
    - 使用 `curl` 或 Python `httpx` 客户端连接 SSE 端点，验证数据流格式。
3.  **并发测试**:
    - 同时启动 2 个回测，确保互不干扰。
