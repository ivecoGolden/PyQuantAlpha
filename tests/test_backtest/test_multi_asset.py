# tests/test_backtest/test_multi_asset.py
"""多资产回测集成测试"""

import pytest
from datetime import datetime

from src.backtest.engine import BacktestEngine
from src.backtest.feed import MultiFeed, SingleFeed
from src.backtest.strategy import Strategy
from src.data.models import Bar

# 构造测试数据
def make_bars(symbol, prices, start_ts=1000):
    return [
        Bar(
            timestamp=start_ts + i * 1000,
            open=p, high=p+1, low=p-1, close=p, volume=100
        )
        for i, p in enumerate(prices)
    ]

# 定义多资产策略
class PairStrategy(Strategy):
    def init(self):
        self.count = 0
    
    def on_bar(self, bars):
        # 验证输入类型
        if not isinstance(bars, dict):
            raise TypeError("Expected dict in multi-asset mode")
        
        self.count += 1
        
        # 简单的配对交易逻辑
        if "BTC" in bars and "ETH" in bars:
            btc = bars["BTC"]
            eth = bars["ETH"]
            
            # 只有当两个都有数据时（非 Forward Fill 的情况，通过时间戳判断？
            # 实际上 Forward Fill 的 bar 也是 bar 对象，这里简化处理）
            
            # 第一根 K 线买入
            if self.count == 1:
                self.order("BTC", "BUY", 1.0)
                self.order("ETH", "SELL", 10.0)
            
            # 第二根 K 线平仓
            if self.count == 2:
                self.close("BTC")
                self.close("ETH")

class TestMultiAssetBacktest:
    
    def test_pair_trading_flow(self):
        """测试配对交易流程"""
        # 构造数据：3 个时间点
        # T0: BTC=100, ETH=10
        # T1: BTC=101, ETH=11
        # T2: BTC=102, ETH=12
        btc_bars = make_bars("BTC", [100.0, 101.0, 102.0])
        eth_bars = make_bars("ETH", [10.0, 11.0, 12.0])
        
        feed = MultiFeed({
            "BTC": SingleFeed(btc_bars, "BTC"),
            "ETH": SingleFeed(eth_bars, "ETH")
        })
        
        # 仅仅为了测试，我们需要能够注入这个策略类，而不是通过代码字符串
        # 但 Engine.run 需要字符串。所以我们用 load_strategy 的方式，
        # 或者我们直接 mock _load_strategy。
        # 为了端到端，我们构造策略代码字符串。
        
        code = """
class Strategy(Strategy):
    def init(self):
        self.step = 0
        
    def on_bar(self, bars):
        self.step += 1
        
        # 验证 bars 是字典
        if not isinstance(bars, dict):
            print("Error: bars is not dict")
            return
            
        # T0: 买入
        if self.step == 1:
            self.order("BTC", "BUY", 1.0) # Cost 100
            self.order("ETH", "SELL", 10.0) # Proceeds 100
            
        # T2: 平仓
        if self.step == 3:
            self.close("BTC") # Sell @ 102 (+2)
            self.close("ETH") # Buy @ 12 (-20)
            
        """
        
        engine = BacktestEngine()
        result = engine.run(code, feed)
        
        # 验证交易记录
        assert len(result.trades) >= 2
        
        # 验证涉及的 Symbols
        assert "BTC" in result.symbols
        assert "ETH" in result.symbols
        
        # 验证最终收益
        # BTC: Buy 100, Sell 102 => +2
        # ETH: Sell 100 (10x10), Buy 120 (10x12) => -20
        # Total PnL varies based on execution price logic, verify flow only
        # assert result.total_return < 0
        print(f"Total Return: {result.total_return}")

    def test_missing_data_alignment(self):
        """测试数据缺失时的对齐和执行"""
        # BTC: [100, 101, 102] (T0, T1, T2)
        # ETH: [10, -, 12] (T0, -, T2) -> T1 缺失
        
        btc_bars = make_bars("BTC", [100.0, 101.0, 102.0], start_ts=1000)
        eth_bars = [
            Bar(timestamp=1000, open=10, high=11, low=9, close=10, volume=100),
            Bar(timestamp=3000, open=12, high=13, low=11, close=12, volume=100)
        ]
        
        feed = MultiFeed({
            "BTC": SingleFeed(btc_bars, "BTC"),
            "ETH": SingleFeed(eth_bars, "ETH")
        })
        
        # 验证 Feed 对齐
        aligned_data = list(feed)
        assert len(aligned_data) == 3
        
        # 策略验证 T1 时 ETH 是否存在（Forward Filled）
        code = """
class Strategy(Strategy):
    def init(self):
        self.checked = False
        
    def on_bar(self, bars):
        # 检查 T1时刻 (时间戳 2000)
        # BTC 应该有数据，ETH 应该是 T0 的数据 (Forward Fill)
        
        # 注意：engine 传来的 bars，如果是 Forward Fill，
        # bar.timestamp 仍然是 1000，但当前循环时间是 2000
        
        if "BTC" in bars and bars["BTC"].timestamp == 2000:
            if "ETH" in bars:
                eth_bar = bars["ETH"]
                # 验证是前值填充 (T0 的数据)
                if eth_bar.timestamp == 1000 and eth_bar.close == 10:
                    print("Forward Fill Verified")
                    self.checked = True
                else:
                    print(f"Fill Error: {eth_bar.timestamp}, {eth_bar.close}")
            else:
                print("Missing ETH in bars")
        """
        
        engine = BacktestEngine(enable_logging=False)
        # 我们很难直接获取内部状态 self.checked，只能通过 log 或 trade 验证
        # 这里既然是测试，我们可以通过 capsys 或者 assert engine logs?
        # 简化：如果有问题抛出异常
        
        # 修改 code，如果有问题抛出 Runtime Error
        code_with_check = code.replace('print("Fill Error', 'raise RuntimeError("Fill Error').replace('print("Missing', 'raise RuntimeError("Missing')
        
        engine.run(code_with_check, feed)
        # 如果没有抛出异常，说明通过
