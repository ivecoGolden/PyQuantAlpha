# 回测能力差距分析报告：PyQuantAlpha vs Backtrader

## 执行摘要

**PyQuantAlpha**：专为 AI 快速生成策略设计的轻量级回测工具，注重简洁与验证速度。
**Backtrader**：Python 生态中最成熟、功能最丰富的量化回测与实盘框架。

**当前状态**：PyQuantAlpha 的回测能力约为 Backtrader 的 **10%**。目前仅实现了 "Hello World" 级别的策略运行环境，缺乏严肃量化交易所需的关键特性（如风险管理订单、资金管理、多资产分析等）。

---

## 功能对比矩阵

| 功能维度 | PyQuantAlpha | Backtrader | 差距/影响 |
| :--- | :--- | :--- | :--- |
| **核心架构** | 简单事件循环 (`for bar in data`) | 基于队列的事件驱动 (`Cerebro`) | PyQuantAlpha 易于调试，但在处理复杂事件/多策略时扩展性差。 |
| **数据源** | 单一 K 线列表 | 多数据源支持、重采样 (Resampling)、回放 | **关键差距**：无法交易配对策略（如 BTC vs ETH）或多周期策略。 |
| **订单类型** | `MARKET` (市价), `LIMIT` (限价) | `STOP` (止损), `STOPLIMIT`, `OCO`, `TARGET` | **关键差距**：策略无法实现真正的止损逻辑，需手动模拟。 |
| **仓位管理** | 手动 (在策略中硬编码数量) | `Sizers` (固定金额、百分比、凯利公式) | 资金利用率低，难以进行资金管理实验。 |
| **指标系统** | Python 类 (需手动 `update`) | `LineSeries` (惰性计算、算术运算支持) | Backtrader 的 `sma1 > sma2` 语法更具声明性，代码更少。 |
| **佣金模型** | 简单费率 (如 0.1%) | 复杂方案 (按股/按单/融资利息) | 对于期货/合约交易，PnL 计算不够精确。 |
| **参数优化** | 无 | 内置网格搜索 (Grid Search) | 无法自动寻找策略的最佳参数。 |
| **可视化** | 无 (仅 JSON 输出) | 内置 Matplotlib 绘图 | 无法直观查看买卖点，调试困难。 |
| **实盘交易** | 无 (仅回测) | 支持 IB, Oanda, CCXT (Binance) | PyQuantAlpha 需要单独开发实盘执行引擎。 |

---

## 详细差距分析

### 1. 风险管理 (止损单)
*   **Backtrader**：支持 `Stop` 单，只有价格触及触发价时才激活。这对于模拟真实的止损至关重要，避免了在 `on_bar` 中手动判断造成的滑点误差或逻辑错误。
*   **PyQuantAlpha**：仅支持市价和限价。策略必须在代码中写 `if low < stop_price` 逻辑，容易出错且不够专业。

### 2. 多数据支持 (Multi-Data)
*   **Backtrader**：支持 `self.datas[0]` (BTC), `self.datas[1]` (ETH)。可以轻松实现 "当 BTC 上涨时买入 ETH" 的逻辑。
*   **PyQuantAlpha**：引擎仅接受单个 `data: List[Bar]`。严格限制在单资产回测。

### 3. 指标生态
*   **Backtrader**：逻辑解耦。`self.sma = bt.ind.SMA(period=20)`。引擎自动处理索引对齐和计算。
*   **PyQuantAlpha**：策略必须每一根 Bar 手动调用 `self.ma.update(bar.close)`。这是 "命令式" 写法，不够优雅，且容易漏掉更新。

### 4. 代码结构
*   **Backtrader 写法**：
    ```python
    def next(self):
        if self.sma[0] > self.data.close[0]:  # 声明式比较
            self.buy()
    ```
*   **PyQuantAlpha 写法**：
    ```python
    def on_bar(self, bar):
        v = self.sma.update(bar.close)    # 必须手动更新状态
        if v and bar.close < v:
             self.order(...)
    ```
    *PyQuantAlpha 的写法对普通 Python 开发者更直观，但牺牲了向量化计算的潜力和代码的简洁性。*

---

## 后续步骤建议 (Recommendations)

为了在不过度设计的前提下弥补关键差距：

1.  **高优先级：添加止损单 (Stop Orders)**
    *   在 `BacktestEngine._match_orders` 中实现 `STOP` 和 `STOP_LIMIT` 逻辑。
    *   这是构建"真实可用"交易策略的最低门槛。

2.  **中优先级：扩展指标库**
    *   尝试统一接口，减少手动 `.update()` 调用。
    *   补充 `RSI`, `MACD`, `ATR`, `BollingerBands` 等常用指标 (已在进行中)。

3.  **中优先级：可视化**
    *   前端利用 Highcharts/TradingView 图表展示回测结果。
    *   在图表上标记买卖点，替代纯 JSON 输出。

4.  **低优先级：仓位管理 (Sizers) 与 优化**
    *   由于我们有 AI，可以通过调整 Prompt 让 AI 优化参数，暂不需要传统的网格搜索。
