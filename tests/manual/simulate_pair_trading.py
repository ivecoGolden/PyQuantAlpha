
"""
复杂策略模拟: 多资产配对交易 (Poly-Asset Pair Trading)
=====================================================

这是一个展示系统当前能力上限的复杂策略示例。

策略原理 (Strategy Logic):
------------------------
1.  **多资产联动 (Cross-Asset)**:
    - 同时订阅 BTCUSDT 和 ETHUSDT 两个交易对。
    - 假设存在长期协整关系 (Cointegration)，即价格比率在一定范围内波动。

2.  **统计套利 (Statistical Arbitrage)**:
    - 计算价差: Spread = Close_BTC - (Close_ETH * HedgeRatio)
    - 维护价差的历史窗口 (window=20)，计算均值 (Mean) 和标准差 (Std)。
    - 计算 Z-Score = (Spread - Mean) / Std。

3.  **交易信号 (Signals)**:
    - **做空价差 (Short Spread)**: 当 Z-Score > 2.0 (价差过大)，卖出 BTC，买入 ETH (对冲)。
    - **做多价差 (Long Spread)**: 当 Z-Score < -2.0 (价差过小)，买入 BTC，卖出 ETH (对冲)。
    - **均值回归 (Mean Reversion)**: 当 |Z-Score| < 0.5 (回归正常)，平仓所有头寸。

4.  **动态风控 (Dynamic Risk Management)**:
    - **动态止损**: 使用 ATR (平均真实波幅) 计算动态止损位。
    - **止损单 (STOP Order)**: 开仓同时挂出 STOP 单，一旦价格反向突破 2*ATR 即止损。

5.  **数据流 (Data Flow)**:
    - 输入: Dict[str, Bar] (多资产对齐数据)
    - 输出: 交易指令 (Orders)
"""

import sys
import os
import random
from typing import Dict
sys.path.append(os.getcwd())

from src.backtest.engine import BacktestEngine
from src.backtest.strategy import Strategy
from src.backtest.feed import MultiFeed, SingleFeed
from src.data.models import Bar
from src.indicators import SMA, ATR

# 1. 定义策略
class PairStrategy(Strategy):
    def init(self):
        print("Strategy Initializing...")
        self.sma_btc = SMA(20)
        self.sma_eth = SMA(20)
        self.atr = ATR(14)
        self.spread_history = []
        self.spread_mean = 0
        self.spread_std = 0
    
    def on_bar(self, bars: dict):
        # Data validation
        if "BTCUSDT" not in bars or "ETHUSDT" not in bars:
            return
            
        bar_btc = bars["BTCUSDT"]
        bar_eth = bars["ETHUSDT"]
        
        # Update indicators
        self.sma_btc.update(bar_btc.close)
        self.sma_eth.update(bar_eth.close)
        atr_val = self.atr.update(bar_btc.high, bar_btc.low, bar_btc.close)
        
        # Need history to calculate z-score
        # Assumed hedge ratio: 1 BTC ~ 14.5 ETH (simplified for mock data)
        spread = bar_btc.close - (bar_eth.close * 14.5)
        self.spread_history.append(spread)
        
        if len(self.spread_history) > 20: 
            self.spread_history.pop(0)
            self.spread_mean = sum(self.spread_history) / len(self.spread_history)
            variance = sum((x - self.spread_mean) ** 2 for x in self.spread_history) / len(self.spread_history)
            self.spread_std = variance ** 0.5
        
        if not (self.spread_std and atr_val):
            return

        # Trading Signals
        z_score = (spread - self.spread_mean) / self.spread_std
        
        # Log periodically
        # if random.random() < 0.05:
        #    print(f"Time: {bar_btc.timestamp}, Spread: {spread:.2f}, Z: {z_score:.2f}, Pos: {self.get_position('BTCUSDT')}")

        # Short Spread: BTC is too expensive relative to ETH
        if z_score > 2.0:
            if not self.get_position("BTCUSDT"):
                print(f"[Signal] SHORT Spread @ {bar_btc.timestamp}: Spread={spread:.2f} (Z={z_score:.2f})")
                self.order("BTCUSDT", "SELL", 0.1)
                self.order("ETHUSDT", "BUY", 1.45) # Hedge
                
                # Stop Loss
                stop_price = bar_btc.close + (atr_val * 2)
                self.order("BTCUSDT", "BUY", 0.1, exectype="STOP", trigger=stop_price)
                
        # Long Spread: BTC is too cheap
        elif z_score < -2.0:
            if not self.get_position("BTCUSDT"):
                print(f"[Signal] LONG Spread @ {bar_btc.timestamp}: Spread={spread:.2f} (Z={z_score:.2f})")
                self.order("BTCUSDT", "BUY", 0.1)
                self.order("ETHUSDT", "SELL", 1.45)

        # Exit (Mean Reversion)
        elif abs(z_score) < 0.5:
             pos_btc = self.get_position("BTCUSDT")
             if pos_btc:
                 print(f"[Signal] EXIT Spread @ {bar_btc.timestamp}: Spread={spread:.2f} (Z={z_score:.2f})")
                 self.close("BTCUSDT")
                 self.close("ETHUSDT")

    def notify_order(self, order):
        if order.status == "FILLED":
            print(f">>> ORDER FILLED: {order.symbol} {order.side.value} {order.quantity} @ {order.filled_avg_price:.2f}")
        elif order.status == "REJECTED":
            print(f"!!! ORDER REJECTED: {order.error_msg}")

# 2. 生成模拟数据
def make_data():
    btc_prices = [50000.0]
    eth_prices = [3450.0] # Ratio ~ 14.5
    
    # 200 bars
    for i in range(200):
        # correlated walk
        move = (random.random() - 0.5) * 100
        btc_p = btc_prices[-1] + move
        
        # eth follows mostly, but diverges sometimes
        eth_move = (move / 14.5) + (random.random() - 0.5) * 10 
        eth_p = eth_prices[-1] + eth_move
        
        # force divergence at some point
        if 50 < i < 80:
            btc_p += 100 # BTC spikes up
            
        btc_prices.append(btc_p)
        eth_prices.append(eth_p)
        
    def to_bars(symbol, prices):
        bars = []
        for i, p in enumerate(prices):
            bars.append(Bar(
                timestamp=1000 + i*60000,
                open=p, high=p+5, low=p-5, close=p, volume=100
            ))
        return bars

    return to_bars("BTCUSDT", btc_prices), to_bars("ETHUSDT", eth_prices)

# 3. 运行回测
if __name__ == "__main__":
    btc_bars, eth_bars = make_data()
    print(f"Data Generated: {len(btc_bars)} bars")
    
    feed = MultiFeed({
        "BTCUSDT": SingleFeed(btc_bars, "BTCUSDT"),
        "ETHUSDT": SingleFeed(eth_bars, "ETHUSDT")
    })
    
    # Using 'Strategy' class defined above, but Engine expects code string or file?
    # Actually Engine._load_strategy loads from string.
    # To run local class instance, we might need a small hack or just pass the code.
    # Let's pass the code string to be safe and consistent with Engine design.
    
    import inspect
    code_source = inspect.getsource(PairStrategy)
    
    # Fix indentation if inside main? No, inspect gets raw source.
    # But it wraps it in "class PairStrategy". The engine expects "class Strategy".
    # Rename for the engine.
    code_source = code_source.replace("class PairStrategy", "class Strategy")
    
    engine = BacktestEngine(enable_logging=True)
    result = engine.run(code_source, feed)
    
    print("\n=== Backtest Results ===")
    print(f"Total Return: {result.total_return:.2%}")
    print(f"Trades: {result.total_trades}")
    for t in result.trades:
        print(f"  [{t.timestamp}] {t.symbol} {t.side.value} {t.quantity} @ {t.price:.2f} PnL:{t.pnl:.2f}")
