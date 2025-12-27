#!/usr/bin/env python
# tests/manual/test_e2e_complex_strategy.py
"""
端到端测试：自然语言生成复杂策略并运行回测

生成 Markdown 格式的完整报告，包含：
1. 输入的自然语言
2. LLM 回复的策略代码
3. 回测执行的所有交易日志
4. 回测最终结果
5. 统计各个环节所消耗的时间
6. 其他重要信息

运行方式:
    conda activate pyquantalpha
    python tests/manual/test_e2e_complex_strategy.py
"""

import os
import sys
import time
from pathlib import Path
from datetime import datetime

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv
load_dotenv()


# 极其复杂的策略描述（自然语言）
# 专门设计用于展示 Phase 3.3 的所有新功能
COMPLEX_STRATEGY_PROMPT = """
请生成一个专业级量化交易策略，**必须使用以下所有新功能**：

## 1. 多指标融合体系
- 使用 EMA(20) 和 EMA(60) 构建趋势判断系统
- 使用 RSI(14) 判断超买超卖区域
- 使用 ATR(14) 计算动态止损止盈距离
- 使用 BollingerBands(20, 2.0) 判断价格相对位置

## 2. 入场条件（必须同时满足多个条件）
- 做多条件：EMA20 > EMA60（趋势向上）且 RSI < 40（超卖）且价格触及布林带下轨
- 做空条件：EMA20 < EMA60（趋势向下）且 RSI > 60（超买）且价格触及布林带上轨

## 3. 重要：仓位管理（必须使用 setsizer）
**必须在 init() 中调用以下代码之一：**
- `self.setsizer("risk", risk_percent=2, atr_multiplier=2)` - 基于 ATR 风险控制仓位
- 或 `self.setsizer("percent", percent=10)` - 按账户净值百分比计算

## 4. 重要：高级订单类型（必须使用以下之一）

### 方案 A：使用挂钩订单 (Bracket Order)
```python
# 买入时自动创建止损+止盈订单
self.buy_bracket("BTCUSDT", size=quantity, stopprice=stop_price, limitprice=take_profit)
```

### 方案 B：使用移动止损 (Trailing Stop)
```python
# 持仓后创建移动止损
self.trailing_stop("BTCUSDT", size=quantity, trailpercent=0.03)  # 3% 追踪
```

## 5. 交易回调（必须实现）
- `notify_order(self, order)` - 打印订单状态
- `notify_trade(self, trade)` - 打印交易盈亏

## 6. 交易对
交易对：BTCUSDT

## 重要提示
- 必须使用 `self.setsizer()` 设置仓位管理
- 必须使用 `self.buy_bracket()` 或 `self.sell_bracket()` 或 `self.trailing_stop()`
- 这些是平台的新功能，请务必使用
"""


class MarkdownReportGenerator:
    """Markdown 报告生成器"""
    
    def __init__(self):
        self.sections = []
        self.timings = {}
        self.start_time = time.time()
    
    def add_header(self, title: str):
        self.sections.append(f"# {title}\n")
        self.sections.append(f"> 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    def add_section(self, title: str, content: str, level: int = 2):
        prefix = "#" * level
        self.sections.append(f"\n{prefix} {title}\n")
        self.sections.append(content)
    
    def add_code_block(self, code: str, language: str = "python"):
        self.sections.append(f"\n```{language}\n{code}\n```\n")
    
    def add_table(self, headers: list, rows: list):
        header_row = "| " + " | ".join(headers) + " |"
        separator = "| " + " | ".join(["---"] * len(headers)) + " |"
        data_rows = "\n".join(["| " + " | ".join(str(c) for c in row) + " |" for row in rows])
        self.sections.append(f"\n{header_row}\n{separator}\n{data_rows}\n")
    
    def start_timing(self, name: str):
        self.timings[name] = {"start": time.time()}
    
    def end_timing(self, name: str):
        if name in self.timings:
            self.timings[name]["end"] = time.time()
            self.timings[name]["duration"] = self.timings[name]["end"] - self.timings[name]["start"]
    
    def add_timing_summary(self):
        self.add_section("耗时统计", "")
        rows = []
        total = 0
        for name, data in self.timings.items():
            if "duration" in data:
                duration = data["duration"]
                total += duration
                rows.append([name, f"{duration:.2f}s"])
        rows.append(["**总耗时**", f"**{total:.2f}s**"])
        self.add_table(["环节", "耗时"], rows)
    
    def generate(self) -> str:
        return "\n".join(self.sections)
    
    def save(self, filepath: str):
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(self.generate())


def test_e2e_complex_strategy() -> None:
    """端到端测试：生成 Markdown 报告"""
    
    report = MarkdownReportGenerator()
    report.add_header("PyQuantAlpha 端到端测试报告")
    
    # ========================
    # 1. 输入的自然语言
    # ========================
    report.add_section("1. 输入的自然语言", "")
    report.add_code_block(COMPLEX_STRATEGY_PROMPT.strip(), "")
    
    # ========================
    # 2. LLM 初始化
    # ========================
    report.start_timing("LLM 初始化")
    
    from src.ai.factory import create_llm_client, LLMProvider
    
    deepseek_key = os.getenv("DEEPSEEK_API_KEY")
    openai_key = os.getenv("OPENAI_API_KEY")
    
    if deepseek_key:
        provider = LLMProvider.DEEPSEEK
        api_key = deepseek_key
    elif openai_key:
        provider = LLMProvider.OPENAI
        api_key = openai_key
    else:
        report.add_section("❌ 错误", "未找到 API Key，请设置 DEEPSEEK_API_KEY 或 OPENAI_API_KEY")
        print(report.generate())
        return
    
    try:
        client = create_llm_client(provider, api_key)
    except Exception as e:
        report.add_section("❌ 错误", f"LLM 客户端初始化失败: {e}")
        print(report.generate())
        return
    
    report.end_timing("LLM 初始化")
    
    # ========================
    # 3. 调用 LLM 生成策略
    # ========================
    report.start_timing("LLM 策略生成")
    
    try:
        response = client.unified_chat(COMPLEX_STRATEGY_PROMPT)
    except Exception as e:
        report.add_section("❌ 错误", f"LLM 请求失败: {e}")
        print(report.generate())
        return
    
    report.end_timing("LLM 策略生成")
    
    if response.type != "strategy" or not response.code:
        report.add_section("❌ 错误", f"未返回策略代码，响应类型: {response.type}")
        print(report.generate())
        return
    
    strategy_code = response.code
    
    # 2. LLM 回复的策略代码
    report.add_section("2. LLM 生成的策略代码", "")
    report.add_section("策略信息", "", level=3)
    report.add_table(
        ["属性", "值"],
        [
            ["LLM Provider", provider.value],
            ["响应类型", response.type],
            ["交易对", ", ".join(response.symbols) if response.symbols else "BTCUSDT"],
            ["代码长度", f"{len(strategy_code)} 字符"],
            ["代码行数", f"{len(strategy_code.splitlines())} 行"]
        ]
    )
    report.add_section("完整代码", "", level=3)
    report.add_code_block(strategy_code, "python")
    
    # 验证代码
    report.start_timing("代码验证")
    from src.backtest.loader import validate_strategy_code
    is_valid, error_msg = validate_strategy_code(strategy_code)
    report.end_timing("代码验证")
    
    if not is_valid:
        report.add_section("❌ 代码验证失败", error_msg)
        print(report.generate())
        return
    
    report.add_section("代码验证", "✅ 验证通过", level=3)
    
    # ========================
    # 4. 获取市场数据
    # ========================
    report.start_timing("获取市场数据")
    
    from src.data.binance import BinanceClient
    
    binance = BinanceClient()
    symbol = response.symbols[0] if response.symbols else "BTCUSDT"
    
    try:
        bars = binance.get_historical_klines(symbol, "1h", days=60)
    except Exception as e:
        try:
            bars = binance.get_klines(symbol, "1h", limit=1000)
        except Exception as e2:
            report.add_section("❌ 错误", f"获取数据失败: {e2}")
            print(report.generate())
            return
    
    report.end_timing("获取市场数据")
    
    report.add_section("3. 市场数据", "")
    report.add_table(
        ["属性", "值"],
        [
            ["交易对", symbol],
            ["K线数量", f"{len(bars)} 根"],
            ["时间范围", f"{datetime.fromtimestamp(bars[0].timestamp/1000)} ~ {datetime.fromtimestamp(bars[-1].timestamp/1000)}"],
            ["价格范围", f"${min(b.low for b in bars):.2f} ~ ${max(b.high for b in bars):.2f}"]
        ]
    )
    
    # ========================
    # 5. 运行回测
    # ========================
    report.start_timing("回测执行")
    
    from src.backtest.engine import BacktestEngine
    from src.backtest.models import BacktestConfig
    
    config = BacktestConfig(
        initial_capital=100000.0,
        commission_rate=0.001,
        slippage=0.0005
    )
    
    engine = BacktestEngine(config=config)
    
    try:
        result = engine.run(strategy_code, bars)
    except Exception as e:
        report.add_section("❌ 回测失败", str(e))
        import traceback
        report.add_code_block(traceback.format_exc(), "")
        print(report.generate())
        return
    
    report.end_timing("回测执行")
    
    # 3. 回测执行的所有交易日志
    report.add_section("4. 交易日志", "")
    
    if result.trades:
        trade_rows = []
        for trade in result.trades:
            time_str = datetime.fromtimestamp(trade.timestamp / 1000).strftime("%Y-%m-%d %H:%M")
            pnl_str = f"{trade.pnl:+.2f}" if trade.pnl != 0 else "0.00"
            trade_rows.append([
                time_str,
                trade.symbol,
                trade.side.value,
                f"{trade.quantity:.4f}",
                f"${trade.price:.2f}",
                f"${pnl_str}",
                f"${trade.fee:.2f}"
            ])
        
        report.add_table(
            ["时间", "交易对", "方向", "数量", "价格", "PnL", "手续费"],
            trade_rows
        )
        
        # 交易统计
        buys = [t for t in result.trades if t.side.value == "BUY"]
        sells = [t for t in result.trades if t.side.value == "SELL"]
        winning = [t for t in result.trades if t.pnl > 0]
        losing = [t for t in result.trades if t.pnl < 0]
        
        report.add_section("交易统计", "", level=3)
        stats_rows = [
            ["总交易次数", len(result.trades)],
            ["买入次数", len(buys)],
            ["卖出次数", len(sells)],
            ["盈利交易", len(winning)],
            ["亏损交易", len(losing)],
            ["总手续费", f"${sum(t.fee for t in result.trades):.2f}"]
        ]
        if winning:
            stats_rows.append(["平均盈利", f"${sum(t.pnl for t in winning)/len(winning):.2f}"])
            stats_rows.append(["最大单笔盈利", f"${max(t.pnl for t in winning):.2f}"])
        if losing:
            stats_rows.append(["平均亏损", f"${sum(t.pnl for t in losing)/len(losing):.2f}"])
            stats_rows.append(["最大单笔亏损", f"${min(t.pnl for t in losing):.2f}"])
        
        report.add_table(["指标", "值"], stats_rows)
    else:
        report.sections.append("\n> 无交易记录\n")
    
    # 4. 回测最终结果
    report.add_section("5. 回测结果", "")
    
    report.add_section("核心指标", "", level=3)
    report.add_table(
        ["指标", "值"],
        [
            ["总收益率", f"{result.total_return:.2%}"],
            ["年化收益率", f"{result.annualized_return:.2%}"],
            ["最大回撤", f"{result.max_drawdown:.2%}"],
            ["夏普比率", f"{result.sharpe_ratio:.2f}"],
            ["胜率", f"{result.win_rate:.2%}"],
            ["盈亏比", f"{result.profit_factor:.2f}"],
            ["总交易次数", result.total_trades]
        ]
    )
    
    # 净值分析
    if result.equity_curve:
        equities = [e["equity"] for e in result.equity_curve]
        report.add_section("净值分析", "", level=3)
        report.add_table(
            ["指标", "值"],
            [
                ["初始净值", f"${equities[0]:,.2f}"],
                ["最终净值", f"${equities[-1]:,.2f}"],
                ["最高净值", f"${max(equities):,.2f}"],
                ["最低净值", f"${min(equities):,.2f}"],
                ["净值波动", f"${max(equities) - min(equities):,.2f}"]
            ]
        )
    
    # 5. 耗时统计
    report.add_timing_summary()
    
    # 6. 其他重要信息
    report.add_section("7. 测试环境", "")
    report.add_table(
        ["项目", "值"],
        [
            ["Python 版本", sys.version.split()[0]],
            ["LLM Provider", provider.value],
            ["初始资金", f"${config.initial_capital:,.2f}"],
            ["手续费率", f"{config.commission_rate:.2%}"],
            ["滑点", f"{config.slippage:.4%}"],
            ["数据周期", "1h"],
            ["回测天数", "60"]
        ]
    )
    
    # 策略评分
    report.add_section("8. 策略评分", "")
    score = 0
    notes = []
    
    if result.total_trades > 0:
        score += 20
        notes.append("✅ 成功产生交易")
    else:
        notes.append("❌ 未产生交易")
    
    if result.total_return > 0:
        score += 30
        notes.append(f"✅ 总收益为正 ({result.total_return:.2%})")
    elif result.total_return > -0.1:
        score += 10
        notes.append(f"⚠️ 总收益轻微亏损 ({result.total_return:.2%})")
    else:
        notes.append(f"❌ 总收益严重亏损 ({result.total_return:.2%})")
    
    if result.win_rate > 0.5:
        score += 20
        notes.append(f"✅ 胜率高于 50% ({result.win_rate:.1%})")
    elif result.win_rate > 0:
        score += 10
        notes.append(f"⚠️ 胜率低于 50% ({result.win_rate:.1%})")
    
    if result.max_drawdown > -0.2:
        score += 20
        notes.append(f"✅ 最大回撤可控 ({result.max_drawdown:.2%})")
    else:
        notes.append(f"❌ 最大回撤过大 ({result.max_drawdown:.2%})")
    
    if result.sharpe_ratio > 1:
        score += 10
        notes.append(f"✅ 夏普比率优秀 ({result.sharpe_ratio:.2f})")
    elif result.sharpe_ratio > 0:
        score += 5
        notes.append(f"⚠️ 夏普比率一般 ({result.sharpe_ratio:.2f})")
    
    report.sections.append(f"\n**总评分: {score}/100**\n")
    for note in notes:
        report.sections.append(f"- {note}\n")
    
    # 生成并保存报告
    report_content = report.generate()
    report_path = project_root / "reports"
    report_path.mkdir(exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_file = report_path / f"e2e_test_report_{timestamp}.md"
    report.save(str(report_file))
    
    print(f"\n📄 报告已保存到: {report_file}")
    print("\n" + "=" * 70)
    print(report_content)


if __name__ == "__main__":
    test_e2e_complex_strategy()
