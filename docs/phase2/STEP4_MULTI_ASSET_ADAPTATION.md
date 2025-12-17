# Phase 2.3b: 多资产策略适配 (Multi-Asset Adaptation)

## 目标
实现真正的多资产回测能力，支持对冲、配对交易和轮动策略。升级数据对齐机制，并改造引擎与策略接口以支持多数据流。

## 任务拆解

### 1. [T8] 数据对齐升级 (Data Alignment)
- **现状**: `MultiFeed`目前使用`set.intersection`（内连接），这会导致如果某一资产在某时刻无数据（如停牌或成交稀疏），整个时间点被丢弃。
- **目标**: 实现 **并集时间轴 (Union) + 前值填充 (Forward Fill)**。
- **实现**:
    - 获取所有数据源的时间戳并集。
    - 遍历并集时间轴。
    - 如果某资产当前时间点无数据，使用其上一次的有效数据（Bar）。
    - 标记数据状态（例如 `bar.is_stale = True`，可选）。

### 2. [T9] 引擎适配 (Engine Adaptation)
- **Engine.run**:
    - 识别 `MultiFeed` 输入。
    - 在循环中，`self._current_bar` 变为 `Dict[str, Bar]`。
    - 需要维护每个资产的最新 Bar 缓存，以便在数据缺失时能够快速获取（虽然 Feed 层已经做了 Forward Fill，但 Engine 层也需要感知）。
    - 撮合逻辑 `_broker.process_orders(bar)` 需要改为遍历所有资产进行撮合：`_broker.process_orders(bars: Dict)`。

### 3. [T10] 策略 API 升级 (Strategy API)
- **Strategy.on_bar**:
    - 现有签名: `on_bar(self, bar: Bar)`。
    - **Breaking Change**: 当输入为多资产时，`bar` 参数将是一个 `Dict[str, Bar]`（或者为了向后兼容，增加 `on_bars` 方法？）。
    - **决策**: 为了保持简单性，建议根据 `DataFeed` 类型动态调整。
        - 单资产: `on_bar(self, bar: Bar)` (保持不变)
        - 多资产: `on_bar(self, bars: Dict[str, Bar])` (类型变化)
    - **Strategy.on_bars** (可选): 如果觉得重载 `on_bar` 太混淆，可以引入专用方法。

### 4. [T11] AI Prompt 更新
- 教导 AI 如何编写多资产策略。
- 示例：`bars["BTCUSDT"].close - bars["ETHUSDT"].close`。

## 验证计划
- 编写测试用例：
    - 两个时间戳错开的数据源（例如 A 有 [1, 3], B 有 [2, 3]）。
    - 验证对齐后的时间轴应为 [1, 2, 3]。
    - 验证 Forward Fill 值是否正确。
- 编写一个配对交易策略示例进行验证。
