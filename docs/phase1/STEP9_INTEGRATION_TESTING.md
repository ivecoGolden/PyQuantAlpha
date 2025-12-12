# Step 9: 集成测试 (Integration Testing)

## 0. 目标
验证整个系统（Core -> Data -> AI -> Backtest -> API -> Frontend）协同工作的正确性。

## 1. 测试范围
- **API 集成**: 验证所有 API 端点在组合场景下的行为。
  - `/health`
  - `/api/klines` & `/api/klines/historical`
  - `/api/generate` (Mock LLM)
  - `/api/backtest/run` (Async + SSE stream)
- **回测流程**: 模拟完整的 "生成策略 -> 启动回测 -> 接收流式结果" 流程。
- **静态资源**: 验证前端文件是否可访问。

## 2. 实施计划

### 2.1 创建集成测试文件 `tests/test_integration/test_full_flow.py`
使用 `TestClient` 和 `mock` 模拟外部依赖（Binance, LLM），但串联内部逻辑。

### 2.2 测试场景

#### 场景 1: 系统健康检查与静态资源
- `GET /health` -> 200 OK
- `GET /` -> 200 OK (index.html)
- `GET /static/js/app.js` -> 200 OK

#### 场景 2: 数据获取 (Mock Binance)
- 模拟 `BinanceClient.get_klines` 返回数据。
- `GET /api/klines?symbol=BTCUSDT` -> 返回数据。

#### 场景 3: 完整策略生成与回测流
1. 调用 `POST /api/generate`，Mock LLM 返回有效代码。
2. 使用返回的代码调用 `POST /api/backtest/run`，获取 `task_id`。
3. 使用 `task_id` 连接 `GET /api/backtest/stream/{task_id}`。
4. 解析 SSE 流，验证收到 `progress` 和 `result` 事件。

## 3. 验证命令
```bash
pytest tests/test_integration/ -v
```
