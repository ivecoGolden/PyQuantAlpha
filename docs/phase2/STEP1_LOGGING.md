# Phase 2.1: 增强型日志与可视化 (Logging & Visualization) ✅

**状态**: 已完成

**目标**：实现“透明化回测”，确保每一笔订单的提交、成交、取消以及每一笔完整交易的盈亏都能被记录和可视化，消除“黑盒”状态。

## 1. 技术设计 (Technical Design)

核心设计借鉴 Backtrader，引入 Observer 模式的简化版：**Strategy Hooks (策略钩子)**。

### 1.1 策略回调钩子 (Strategy Hooks)
在 `Strategy` 基类中增加以下回调方法，供用户重写：

```python
class Strategy:
    def notify_order(self, order: Order):
        """
        当订单状态发生变化时触发 (Submitted -> Accepted -> Completed/Canceled/Rejected)
        """
        pass

    def notify_trade(self, trade: Trade):
        """
        当一笔交易 (Trade) 结束（平仓）时触发，包含盈亏信息
        """
        pass
```

### 1.2 结构化日志 (Structured Logging)
改造 `BacktestLogger` (或新建 `Journal`)，使其不仅记录 equity，还记录流水。结构如下：

- **Orders Log**: `[Time, Symbol, Type, ID, Status, Price, Size]`
- **Trades Log**: `[Time, Symbol, PnL, PnL%, EntryPrice, ExitPrice]`

### 1.3 前端可视化协议 (Visualization Protocol)
API 返回的 JSON 数据结构需新增 `markers` 字段：

```json
{
  "equity": [...],
  "markers": [
    {"time": 1678888000, "type": "BUY", "price": 20000, "text": "Buy @ 20000"},
    {"time": 1678899000, "type": "SELL", "price": 21000, "text": "Sell @ 21000, PnL: +5%"}
  ]
}
```

---

## 2. 开发步骤 (Implementation Steps)

### Step 1: 策略层增强 (Strategy Layer)
- [ ] 修改 `src/backtest/strategy.py`:
    - [ ] 添加 `notify_order(self, order)` 占位方法。
    - [ ] 添加 `notify_trade(self, trade)` 占位方法。

### Step 2: 引擎层事件触发 (Engine Layer)
- [ ] 修改 `src/backtest/engine.py` 的 `_match_orders` 方法:
    - [ ] 当订单成交时，调用 `strategy.notify_order(order)`。
    - [ ] **关键**: 识别“平仓”动作。当持仓从有变无，或反向开仓导致原有仓位关闭时，生成 `Trade` 对象（需新建 `Trade` 类记录开平仓价格和盈亏），并调用 `strategy.notify_trade(trade)`。
    - [ ] *暂不实现复杂的 Backtrader `Position` 类，先通过简单逻辑计算平仓盈亏。*

### Step 3: 日志收集器 (Logger)
- [ ] 修改 `src/backtest/logger.py`:
    - [ ] 新增 `log_order(order)` 方法，格式化记录订单信息。
    - [ ] 新增 `log_trade(trade)` 方法，记录盈亏。
    - [ ] 确保这些日志能被前端 API读取（可能需要存储在内存 List 中并在回测结束时返回）。

### Step 4: 前端深度适配 (Frontend Deep Dive)

鉴于目前 `src/api/static` 是基于 **Vanilla JS + Tailwind + Chart.js** 的轻量级实现，我们将在此基础上进行扩展，而不是引入 Vue 或 Highcharts。

#### 4.1 数据协议 (Data Protocol)
API `/api/backtest` 的响应结构将增加 `visuals` 对象：

```json
{
  "equity": [{"x": 1678888000000, "y": 10000}, ...],
  "visuals": {
    "markers": [
      // 买入点 (Green Triangle Up)
      {"x": 1678888000000, "y": 10000, "type": "BUY", "text": "Buy 1.0 @ 20000"},
      // 卖出点 (Red Triangle Down)
      {"x": 1678899000000, "y": 10500, "type": "SELL", "text": "Sell 1.0 @ 21000, PnL: +500"}
    ],
    "logs": [
      {"time": "2023-01-01 10:00:00", "level": "INFO", "msg": "Order Submitted..."},
      {"time": "2023-01-01 10:00:05", "level": "TRADE", "msg": "Trade Closed..."}
    ]
  }
}
```

#### 4.2 Chart.js 图表适配
由于 Chart.js 原生不支持 Flags，我们将通过 **混合图表 (Mixed Chart)** 实现：
- **Dataset 0 (Line)**: 净值曲线。
- **Dataset 1 (Scatter)**: 买卖标记。
    - `pointStyle`: 'triangle' (Buy) / 'rectRot' (Sell - 模拟倒三角).
    - `backgroundColor`: Green (Buy) / Red (Sell).
    - `radius`: 6.

**代码逻辑 (`ui.js` / `chart_utils.js`)**:
```javascript
// 在更新图表数据时：
chart.data.datasets.push({
    type: 'scatter',
    label: 'Trade Markers',
    data: markers, // {x, y} 数组
    pointStyle: ctx => ctx.raw.type === 'BUY' ? 'triangle' : 'rectRot',
    backgroundColor: ctx => ctx.raw.type === 'BUY' ? '#22c55e' : '#ef4444',
    pointRadius: 6
});
```

#### 4.3 日志与交易面板 (Logs & Trades UI)
在 `index.html` 中新增一个 Tab 容器，位于 Chart 下方或右侧侧边栏：
- **DOM 结构**:
  ```html
  <div class="tabs">
      <button onclick="switchTab('logs')">运行日志</button>
      <button onclick="switchTab('trades')">交易明细</button>
  </div>
  <div id="panel-logs" class="overflow-auto font-mono text-xs"></div>
  <div id="panel-trades" class="hidden overflow-auto"></div>
  ```

- **渲染逻辑 (`ui.js`)**:
  - `renderLogs(logs)`: 将日志数组渲染为 `<p class="text-gray-400">...</p>`。
  - `renderTrades(trades)`: 渲染为 HTML Table，包含 `Entry`, `Exit`, `PnL` 等列。

---

## 3. 验证计划 (Verification Plan)

### 3.1 单元测试
- 编写 `tests/test_hooks.py`:
    - 定义一个 TestStrategy，重写 `notify_order` 和 `notify_trade`，在回调中 `print` 或 `append` 到列表。
    - 运行回测，断言列表中捕获到了正确的订单状态变更和交易盈亏。

### 3.2 模拟回测
- 运行一个简单的 `SMA Cross` 策略。
- 检查控制台输出（或日志文件），确认能看到类似以下的日志：
  ```text
  [2023-01-01 10:00] ORDER ACCEPTED: BUY BTCUSDT, Size: 1.0, Price: 20000
  [2023-01-01 10:00] ORDER COMPLETED: BUY BTCUSDT, @ 20005, Comm: 2.0
  [2023-01-02 14:00] TRADE CLOSED: BTCUSDT, PnL: 500.0 (2.5%)
  ```
