# Step 3: 架构优化分析

> Phase 2.2 重构完成后的架构评审与优化建议

---

## 概述

在完成 Phase 2.2（Broker 抽象与高级订单类型）后，对 `src/backtest` 模块进行了代码审查，识别出以下 4 个潜在的架构改进点。本文档对每个问题进行分析，评估其**严重程度**、**是否需要解决**以及**建议的解决时机**。

---

## 问题 1：依赖倒置 - 策略加载耦合 ✅ 已解决

### 原状

`BacktestEngine` 导入了 `src.ai.validator` 模块：

```python
# src/backtest/engine.py:21 (旧)
from src.ai.validator import execute_strategy_code
```

### 解决方案

1. ✅ 创建 `src/backtest/loader.py`，将策略加载逻辑迁移至此
2. ✅ `engine.py` 改为从 `.loader` 导入
3. ✅ `src/ai/validator.py` 改为重新导出（向后兼容）

```python
# src/backtest/engine.py:24 (新)
from .loader import execute_strategy_code
```

### 验证

- 全部 282 测试通过
- `backtest` 模块不再依赖 `ai` 模块

---

## 问题 2：DataFeed 抽象缺失 ✅ 已解决

### 原状

`BacktestEngine.run()` 直接接收 `List[Bar]`，并在内部进行遍历。

### 解决方案

1. ✅ 创建 `src/backtest/feed.py`
   - `DataFeed` 抽象基类
   - `SingleFeed` 单资产实现
   - `MultiFeed` 多资产实现（时间对齐）
   - `create_feed()` 工厂函数

2. ✅ `engine.run()` 支持 `Union[List[Bar], DataFeed]`
   - 向后兼容：仍可传入 `List[Bar]`
   - 内部自动转换为 `SingleFeed`

```python
# src/backtest/engine.py
def run(self, strategy_code: str, data: Union[List[Bar], DataFeed], ...):
    if isinstance(data, list):
        feed = SingleFeed(data) if data else None
    else:
        feed = data
```

### 验证

- 新增 10 个 DataFeed 测试
- 全部 282 测试通过

---

## 问题 3：Strategy 基类缺失 ✅ 已解决

### 原状

策略是一个"鸭子类型"的普通类，API（如 `self.order`）由 Engine 在运行时动态注入。

### 解决方案

1. ✅ 创建 `src/backtest/strategy.py`，定义 `Strategy` 抽象基类
2. ✅ 提供完整的 API 类型提示和文档
3. ✅ 向后兼容：现有"鸭子类型"策略仍可运行

```python
from src.backtest import Strategy

class MyStrategy(Strategy):
    def init(self):
        self.ema = EMA(20)
    
    def on_bar(self, bar):
        # IDE 现在能提供自动补全
        self.order("BTCUSDT", "BUY", 1.0)
```

### 验证

- `Strategy` 基类已导出到 `src.backtest`
- 全部 282 测试通过

---

## 问题 4：订单查找性能 O(N) ✅ 已解决

### 原状

在 `engine._on_trade_filled` 中，通过遍历列表查找订单：

```python
# 旧代码 O(N)
for o in self._broker.orders:
    if o.id == trade.order_id:
        order = o
        break
```

### 解决方案

1. ✅ 在 `BacktestBroker` 中添加 `_orders_map: Dict[str, Order]`
2. ✅ 添加 `get_order(order_id)` 方法，实现 O(1) 查找
3. ✅ 更新 `engine._on_trade_filled` 使用新方法

```python
# 新代码 O(1)
order = self._broker.get_order(trade.order_id)
```

### 验证

- 全部 282 测试通过

---

## 总结与行动计划

| 问题 | 严重程度 | 状态 | 优先级 |
|------|----------|------|--------|
| 1. 依赖倒置 | 🟡 中等 | ✅ 已解决 | P2 |
| 2. DataFeed 缺失 | 🟠 较高 | ✅ 已解决 | P1 |
| 3. Strategy 基类 | 🟢 低 | ✅ 已解决 | P3 |
| 4. 性能优化 | 🟢 低 | ✅ 已解决 | P4 |

### 已完成的工作

1. ✅ **创建 `loader.py`** — 策略加载逻辑迁移，解决依赖倒置
2. ✅ **创建 `feed.py`** — DataFeed 抽象，支持单/多资产
3. ✅ **创建 `strategy.py`** — Strategy 基类，提供 API 类型提示
4. ✅ **优化 `broker.py`** — 添加 `_orders_map` 和 `get_order()` 实现 O(1) 查找
5. ✅ **更新 `engine.py`** — 支持 DataFeed，使用 O(1) 订单查找
6. ✅ **添加测试** — 10 个 DataFeed 测试，总计 282 测试通过

---

## 附录：当前模块结构

```
src/backtest/
├── __init__.py    # 模块导出
├── models.py      # 数据模型 (Order, Trade, Position, ...)
├── broker.py      # Broker 抽象层 (资金、持仓、撮合、O(1)查找)
├── engine.py      # 回测引擎核心 (驱动循环)
├── analyzer.py    # 绩效分析器
├── logger.py      # 日志记录器
├── manager.py     # 异步任务管理 (SSE)
├── loader.py      # 策略加载与校验
├── feed.py        # 数据源抽象 (Single/MultiFeed)
└── strategy.py    # 策略基类 (ABC)
```

**所有架构优化任务已完成** ✅
