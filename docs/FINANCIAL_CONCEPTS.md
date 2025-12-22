# PyQuantAlpha 金融概念指南

本文档旨在通过通俗易懂的语言，详细解释 PyQuantAlpha 项目中涉及的核心金融概念、技术指标算法以及回测评估体系。

---

## 📚 目录

1. [基础数据概念](#1-基础数据概念)
2. [交易操作指南](#2-交易操作指南)
3. [技术指标算法详解](#3-技术指标算法详解)
4. [回测绩效指标](#4-回测绩效指标)
5. [高级技术指标](#5-高级技术指标)
6. [数据处理与多周期](#6-数据处理与多周期)
7. [策略与交易概念](#7-策略与交易概念)
8. [订单类型扩展](#8-订单类型扩展)

---

## 1. 基础数据概念

### K 线 (Candlestick / Bar)
量化交易中最基础的数据单元，反映了一段时间内的价格变动。
- **Open (O)**: 开盘价，该时间段开始时的价格。
- **High (H)**: 最高价，该时间段内达到的最高价格。
- **Low (L)**: 最低价，该时间段内触及的最低价格。
- **Close (C)**: 收盘价，该时间段结束时的价格（最重要，常用于指标计算）。
- **Volume (V)**: 成交量，该时间段内的交易数量。

**时间周期 (Timeframe)**:
K 线代表的时间跨度，如 `1m` (1分钟), `1h` (1小时), `1d` (1天)。

---

## 2. 交易操作指南

### 订单方向 (Side)
- **多头 (Long)**: 预期价格上涨。
    - **买入 (BUY)**: 花费现金购买资产。
    - **平仓 (SELL)**: 卖出持有的资产，获利了结或止损。
- **空头 (Short)**: 预期价格下跌。
    - **卖出 (SELL)**: 借入资产并卖出（开空），获得现金。
    - **买入 (BUY)**: 花费现金买回资产归还（平空/补仓）。

### 订单类型 (Type)
| 类型 | 说明 | 使用场景 |
|-----|------|---------|
| **MARKET** | 以当前市场最优价格立即成交 | 需要快速成交，不在意价格 |
| **LIMIT** | 指定价格成交 | 需要精确价格控制 |
| **STOP** | 价格触发后转为市价单 | 止损、突破追单 |
| **STOP_LIMIT** | 价格触发后转为限价单 | 精确止损、避免滑点 |

### 订单状态生命周期
```
CREATED → SUBMITTED → ACCEPTED → FILLED / REJECTED / CANCELED / EXPIRED
```

| 状态 | 说明 |
|-----|------|
| CREATED | 订单已创建但未提交 |
| SUBMITTED | 已提交给 Broker |
| ACCEPTED | Broker 已受理（预检通过） |
| PARTIAL | 部分成交 |
| FILLED | 全部成交 |
| CANCELED | 已取消 |
| REJECTED | 已拒绝（资金不足/无效参数） |
| EXPIRED | 已过期 |

### 资金管理
- **现金 (Cash)**: 账户中的可用资金。
- **持仓 (Position)**: 当前持有的资产数量（正数为多头，负数为空头）。
- **净值 (Equity)**: 账户总价值 = 现金 + 持仓市值。
    - 多头市值 = 数量 × 当前价格
    - 空头市值（浮动盈亏） = |数量| × (开仓均价 - 当前价格)

---

### 策略交易 API

以下是策略中可用的交易和查询函数：

#### 下单 `order()`
```python
order(symbol, side, quantity, price=None, exectype="MARKET", trigger=None)
```
| 参数 | 类型 | 说明 |
|-----|------|------|
| symbol | str | 交易对，如 "BTCUSDT" |
| side | str | "BUY" 或 "SELL" |
| quantity | float | 数量 |
| price | float | 限价单价格（可选） |
| exectype | str | 订单类型：MARKET/LIMIT/STOP/STOP_LIMIT |
| trigger | float | 止损触发价格（STOP/STOP_LIMIT 必填） |

#### 平仓 `close()`
```python
close(symbol)  # 平掉指定交易对的全部持仓
```

#### 获取持仓 `get_position()`
```python
pos = get_position("BTCUSDT")
if pos:
    print(f"持仓: {pos.quantity}, 均价: {pos.avg_price}")
```

#### 获取资金 `get_cash()` / `get_equity()`
```python
cash = get_cash()      # 可用现金
equity = get_equity()  # 账户净值
```

#### 获取历史 K 线 `get_bars()` / `get_bar()`
```python
bars = get_bars("BTCUSDT", lookback=100)  # 获取最近 100 根 K 线
prev_bar = get_bar("BTCUSDT", offset=-2)  # 获取上一根 K 线
```

---

### 策略回调

#### 订单状态回调 `notify_order()`
当订单状态发生变化（提交、成交、拒绝等）时自动调用。
```python
def notify_order(self, order):
    if order.status == "FILLED":
        print(f"成交: {order.symbol} {order.side} @ {order.filled_avg_price}")
    elif order.status == "REJECTED":
        print(f"拒单: {order.error_msg}")
```

#### 成交回调 `notify_trade()`
当产生盈亏（平仓成交）时自动调用。
```python
def notify_trade(self, trade):
    print(f"交易完成: 盈亏 {trade.pnl:.2f}, 手续费 {trade.fee:.2f}")
```

---

## 3. 技术指标算法详解

### 3.1 移动平均线 (Moving Average)

#### 简单移动平均线 (SMA - Simple Moving Average)
最基础的均线，计算过去 N 个周期收盘价的算术平均值。

**算法**:
$$
SMA_t = \frac{P_t + P_{t-1} + \dots + P_{t-n+1}}{n}
$$
其中 $P$ 为收盘价，$n$ 为周期。

**意义**: 平滑价格波动，反映趋势方向。

#### 指数移动平均线 (EMA - Exponential Moving Average)
对近期价格赋予更高权重的均线，比 SMA 对价格变化反应更灵敏。

**算法**:
$$
EMA_t = (P_t \times \alpha) + (EMA_{t-1} \times (1 - \alpha))
$$
$$
\alpha = \frac{2}{n + 1}
$$
其中 $P_t$ 为今日收盘价，$n$ 为周期。

---

### 3.2 震荡指标 (Oscillators)

#### 相对强弱指数 (RSI - Relative Strength Index)
测量价格变动的速度和变化，用于评估超买或超卖状态。范围 0-100。

**算法**:
1. 计算每日变动 $U$ (Up) 和 $D$ (Down):
   - 如果 $Close_t > Close_{t-1}$: $U = Close_t - Close_{t-1}, D = 0$
   - 如果 $Close_t < Close_{t-1}$: $U = 0, D = Close_{t-1} - Close_t$
2. 计算平均涨幅 $AvgU$ 和平均跌幅 $AvgD$ (通常使用平滑移动平均):
3. 计算相对强弱 $RS$:
   $$ RS = \frac{AvgU}{AvgD} $$
4. 计算 RSI:
   $$ RSI = 100 - \frac{100}{1 + RS} $$

**用法**: 一般 >70 为超买（暗示回调），<30 为超卖（暗示反弹）。

#### 平滑异同移动平均线 (MACD)
趋势跟踪动量指标，显示两条移动平均线之间的关系。

**组成与算法**:
1. **DIF (快线)**: 12日 EMA - 26日 EMA
   $$ DIF = EMA(12) - EMA(26) $$
2. **DEA (信号线)**: DIF 的 9日 EMA
   $$ DEA = EMA(DIF, 9) $$
3. **MACD 柱 (Histogram)**:
   $$ Histogram = (DIF - DEA) \times 2 $$

**用法**: 金叉 (DIF 上穿 DEA) 做多，死叉 (DIF 下穿 DEA) 做空。

---

### 3.3 波动率指标 (Volatility)

#### 布林带 (Bollinger Bands)
由中轨、上轨、下轨组成的带状通道。

**算法**:
1. **中轨 (Middle Band)**: 20日 SMA
2. **标准差 (StdDev)**: 过去20日收盘价的标准差
3. **上轨 (Upper Band)**: 中轨 + (2 × 标准差)
4. **下轨 (Lower Band)**: 中轨 - (2 × 标准差)

**用法**: 价格触及上轨可能回调，触及下轨可能反弹；带宽收窄预示变盘。

#### 平均真实波幅 (ATR - Average True Range)
衡量市场波动性的指标（不指示方向）。

**算法**:
1. 计算真实波幅 (TR): Today's TR = Max of:
   - |今日最高 - 今日最低|
   - |今日最高 - 昨日收盘|
   - |今日最低 - 昨日收盘|
2. ATR = TR 的 N 日移动平均 (通常14日)

**用法**: 常用于设置止损位 (如 2倍 ATR 止损)。

---

## 4. 回测绩效指标

### 总收益率 (Total Return)
策略结束时的总盈亏比例。
**公式**:
$$
Total Return = \frac{最终净值 - 初始本金}{初始本金} \times 100\%
$$

### 年化收益率 (Annualized Return / CAGR)
将总收益率标准化为一年的收益率，便于跨周期比较。
**公式**:
$$
Annualized = (1 + TotalReturn)^{\frac{365}{天数}} - 1
$$

### 最大回撤 (Max Drawdown)
资金曲线从任一高点到其后最低点的最大跌幅，衡量最坏情况下的风险。
**公式**:
$$
MDD = \max \left( \frac{Peak - Trough}{Peak} \right)
$$

### 夏普比率 (Sharpe Ratio)
衡量每承担一单位风险所获得的超额回报。越高越好。
**公式**:
$$
Sharpe = \frac{E(R_p) - R_f}{\sigma_p}
$$
- $E(R_p)$: 策略年化收益率
- $R_f$: 无风险利率 (如 2%)
- $\sigma_p$: 收益率的年化标准差 (波动率)

### 胜率 (Win Rate)
盈利交易次数占总交易次数的比例。
**公式**:
$$
Win Rate = \frac{盈利交易数}{总交易数} \times 100\%
$$

### 盈亏比 (Profit Factor)
总盈利金额与总亏损金额的比值。
**公式**:
$$
Profit Factor = \frac{\sum 盈利金额}{|\sum 亏损金额|}
$$
通常 > 1.5 为优秀，> 1.0 为盈利。

---

## 5. 高级技术指标

### 5.1 趋势强度指标

#### ADX (Average Directional Index) - 平均趋向指标
衡量趋势的**强度**（不区分方向）。

**算法**:
1. 计算 True Range (TR)
2. 计算 +DM (向上动量) 和 -DM (向下动量)
3. 平滑计算 +DI 和 -DI：
   $$ +DI = 100 \times \frac{平滑 +DM}{平滑 TR} $$
4. 计算 DX：
   $$ DX = 100 \times \frac{|+DI - (-DI)|}{+DI + (-DI)} $$
5. ADX = DX 的 N 日移动平均

**用法**: ADX > 25 表示强趋势，ADX < 20 表示弱趋势或横盘震荡。

#### 一目均衡表 (Ichimoku Cloud)
日本技术分析指标，包含五条线，用于判断支撑/阻力和趋势方向。

**组成**:
| 线 | 名称 | 计算 |
|---|------|------|
| 转换线 | Tenkan-sen | (9日最高 + 9日最低) / 2 |
| 基准线 | Kijun-sen | (26日最高 + 26日最低) / 2 |
| 先行带A | Senkou Span A | (转换线 + 基准线) / 2，向前移26日 |
| 先行带B | Senkou Span B | (52日最高 + 52日最低) / 2，向前移26日 |
| 延迟线 | Chikou Span | 当前收盘价，向后移26日 |

**用法**: 价格在云上方为上升趋势，云下方为下降趋势；先行带A/B之间形成"云层"作为支撑/阻力。

---

### 5.2 动量型指标

#### Stochastic (随机指标)
测量收盘价相对于一段时间内价格区间的位置。

**算法**:
$$
\%K = \frac{Close - Lowest_{N}}{Highest_{N} - Lowest_{N}} \times 100
$$
$$
\%D = SMA(\%K, M)
$$
其中 N 通常为 14，M 通常为 3。

**用法**: %K > 80 超买，%K < 20 超卖；%K 上穿 %D 为金叉。

#### Williams %R (威廉指标)
与 Stochastic 类似，但取值范围为 -100 到 0。

**算法**:
$$
\%R = \frac{Highest_{N} - Close}{Highest_{N} - Lowest_{N}} \times (-100)
$$

**用法**: %R < -80 超卖，%R > -20 超买。

#### CCI (Commodity Channel Index) - 顺势指标
衡量价格偏离统计平均值的程度。

**算法**:
1. 典型价格 (TP) = (High + Low + Close) / 3
2. 平均典型价格 = SMA(TP, N)
3. 平均绝对偏差 (MAD) = Σ|TP - 平均TP| / N
4. CCI = (TP - 平均TP) / (0.015 × MAD)

**用法**: CCI > +100 超买，CCI < -100 超卖。

---

### 5.3 成交量型指标

#### OBV (On-Balance Volume) - 能量潮
基于成交量的累积指标，用于判断资金流向。

**算法**:
- 若今日收盘 > 昨日收盘：OBV += 今日成交量
- 若今日收盘 < 昨日收盘：OBV -= 今日成交量
- 若价格不变：OBV 不变

**用法**: OBV 上升表示资金流入，下降表示资金流出。OBV 与价格背离可能预示趋势反转。

---

### 5.4 自定义指标

#### SentimentDisparity (情绪背离指标)
衡量价格走势与账户多空比走势之间的分歧。

**算法**:
$$
Disparity = (Price\_Change\% - Ratio\_Change\%) \times 100
$$

**用法**:
- **正值 (多头背离)**: 价涨但多空比跌 → 散户下车/大户接盘 → 趋势可能延续
- **负值 (空头背离)**: 价跌但多空比涨 → 散户抄底/大户出货 → 可能继续下跌

---

## 6. 数据处理与多周期

### 数据重采样 (Resampling)
将低频 K 线（如 1分钟）聚合为高频 K 线（如 5分钟、1小时）。

**聚合规则**:
| OHLCV 字段 | 聚合方法 |
|-----------|---------|
| Open | 取第一个 Bar 的 Open |
| High | 取所有 Bar 的最大 High |
| Low | 取所有 Bar 的最小 Low |
| Close | 取最后一个 Bar 的 Close |
| Volume | 求和 |

### 多周期对齐 (Multi-Timeframe Alignment)
在回测中使用多周期数据时，必须**严格防止未来函数**。

**原则**: 当策略在小周期（如 5m）运行时，若需查询大周期（如 1h）数据，只能返回**已经收盘**的大周期 Bar。

**示例**: 假设当前时间是 10:35，策略运行在 5m 周期：
- 可以获取 10:00 的 1h Bar（已收盘）
- 不能获取 10:35 正在形成的 1h Bar（会引入未来数据穿越）

---

## 7. 策略与交易概念

### 配对交易 (Pair Trading)
一种市场中性策略，同时做多一个资产、做空另一个相关资产。

**逻辑**:
1. 选择两个高度相关的资产（如 BTC 和 ETH）
2. 计算价差 (Spread) = Asset_A - Asset_B × HedgeRatio
3. 当价差偏离均值时进场，回归均值时平仓

**示例**:
- 价差 > 布林带上轨：做空价差 (卖 A，买 B)
- 价差 < 布林带下轨：做多价差 (买 A，卖 B)

### 对冲比例 (Hedge Ratio)
配对交易中，一个标的的持仓量需要乘以对冲比例来匹配另一个标的。

**公式** (简化):
$$
HedgeRatio = \frac{Price_A}{Price_B}
$$

**示例**: 若 BTC = 50000, ETH = 3500，则 HedgeRatio ≈ 14.3。做多 1 BTC 需做空约 14.3 ETH。

### 止损与止盈 (Stop Loss / Take Profit)
自动平仓的风控机制。

| 类型 | 说明 | 示例 |
|-----|------|-----|
| 固定止损 | 亏损固定金额或比例时平仓 | -5% 止损 |
| ATR 止损 | 基于波动率动态调整 | 入场价 - 2×ATR |
| 固定止盈 | 盈利固定金额或比例时平仓 | +10% 止盈 |
| 移动止盈 | 随着价格上涨不断上移止盈点 | 追踪止损 |

---

## 8. 订单类型扩展

### 止损单 (Stop Order)
当价格达到触发价时，转为市价单执行。

**逻辑**:
- **止损买入 (Buy Stop)**: 价格 ≥ 触发价时买入
- **止损卖出 (Sell Stop)**: 价格 ≤ 触发价时卖出

**用途**: 设置止损位，或在突破时追涨杀跌。

### 止损限价单 (Stop Limit Order)
当价格达到触发价时，转为限价单挂出。

**参数**:
- `stop_price`: 触发价
- `limit_price`: 限价

**优势**: 避免市价单的滑点，但可能因价格快速移动而未成交。

---

*文档更新日期: 2025-12-22*
