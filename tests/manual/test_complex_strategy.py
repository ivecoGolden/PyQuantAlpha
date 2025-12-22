
import sys
import os
import random
import inspect
import math
from typing import Dict, List

# Ensure src is in path
sys.path.append(os.getcwd())

from src.backtest.engine import BacktestEngine
from src.backtest.feed import MultiFeed, SingleFeed
from src.data.models import Bar
# Helper imports for the script scope (not necessarily used inside strategy sandbox if not permitted)
from src.indicators import SMA, ATR, BollingerBands, RSI

# ==========================================
# User's Strategy Code (Paste Verbatim)
# ==========================================
class Strategy:
    def init(self):
        # 初始化BTC指标
        self.bb_btc = BollingerBands(period=20, std_dev=2.0)
        self.rsi_btc = RSI(period=14)
        self.atr_btc = ATR(period=14)
        # 初始化ETH指标
        self.bb_eth = BollingerBands(period=20, std_dev=2.0)
        self.rsi_eth = RSI(period=14)
        self.atr_eth = ATR(period=14)
        # 价差相关
        self.spread_bb = BollingerBands(period=20, std_dev=2.0)
        self.spread_rsi = RSI(period=14)
        self.position_btc = 0.0  # BTC持仓
        self.position_eth = 0.0  # ETH持仓
        self.entry_price = 0.0  # 入场价差
        self.stop_loss = 0.0  # 止损价差
        self.take_profit = 0.0  # 止盈价差
        self.max_position = 1.0  # 最大仓位（单位：BTC）
        self.hedge_ratio = 14.0  # 对冲比例（ETH数量 = BTC数量 * hedge_ratio）
    
    def on_bar(self, bars):
        # 检查数据是否存在
        if "BTCUSDT" not in bars or "ETHUSDT" not in bars:
            return
        bar_btc = bars["BTCUSDT"]
        bar_eth = bars["ETHUSDT"]
        
        # 更新BTC指标
        bb_btc_res = self.bb_btc.update(bar_btc.close)
        rsi_btc_val = self.rsi_btc.update(bar_btc.close)
        atr_btc_val = self.atr_btc.update(bar_btc.high, bar_btc.low, bar_btc.close)
        # 更新ETH指标
        bb_eth_res = self.bb_eth.update(bar_eth.close)
        rsi_eth_val = self.rsi_eth.update(bar_eth.close)
        atr_eth_val = self.atr_eth.update(bar_eth.high, bar_eth.low, bar_eth.close)
        
        # 计算价差（假设对冲比例）
        spread = bar_btc.close - bar_eth.close * self.hedge_ratio
        spread_bb_res = self.spread_bb.update(spread)
        spread_rsi_val = self.spread_rsi.update(spread)
        
        # 检查指标是否有效
        if bb_btc_res is None or rsi_btc_val is None or atr_btc_val is None or \
           bb_eth_res is None or rsi_eth_val is None or atr_eth_val is None or \
           spread_bb_res is None or spread_rsi_val is None:
            return
        
        # 计算平均ATR用于风险
        avg_atr = (atr_btc_val + atr_eth_val * self.hedge_ratio) / 2.0
        
        # 交易逻辑：无持仓时开仓
        if self.position_btc == 0.0 and self.position_eth == 0.0:
            # 做空价差条件：价差突破布林带上轨且RSI超买
            if spread > spread_bb_res.upper and spread_rsi_val > 70:
                # 计算仓位大小（基于ATR风险）
                quantity_btc = min(self.max_position, 0.1 * bar_btc.close / avg_atr) if avg_atr > 0 else 0.1
                quantity_eth = quantity_btc * self.hedge_ratio
                # 下单：卖BTC，买ETH
                self.order("BTCUSDT", "SELL", quantity_btc)
                self.order("ETHUSDT", "BUY", quantity_eth)
                self.position_btc = -quantity_btc
                self.position_eth = quantity_eth
                self.entry_price = spread
                self.stop_loss = spread + 2.0 * avg_atr  # 止损：价差上涨2倍ATR
                self.take_profit = spread - 3.0 * avg_atr  # 止盈：价差下跌3倍ATR
            # 做多价差条件：价差跌破布林带下轨且RSI超卖
            elif spread < spread_bb_res.lower and spread_rsi_val < 30:
                quantity_btc = min(self.max_position, 0.1 * bar_btc.close / avg_atr) if avg_atr > 0 else 0.1
                quantity_eth = quantity_btc * self.hedge_ratio
                # 下单：买BTC，卖ETH
                self.order("BTCUSDT", "BUY", quantity_btc)
                self.order("ETHUSDT", "SELL", quantity_eth)
                self.position_btc = quantity_btc
                self.position_eth = -quantity_eth
                self.entry_price = spread
                self.stop_loss = spread - 2.0 * avg_atr
                self.take_profit = spread + 3.0 * avg_atr
        # 有持仓时平仓逻辑
        else:
            # 止损或止盈
            if (self.position_btc < 0 and spread >= self.stop_loss) or \
               (self.position_btc > 0 and spread <= self.stop_loss) or \
               (self.position_btc < 0 and spread <= self.take_profit) or \
               (self.position_btc > 0 and spread >= self.take_profit):
                # 平仓所有持仓
                if self.position_btc > 0:
                    self.order("BTCUSDT", "SELL", self.position_btc)
                elif self.position_btc < 0:
                    self.order("BTCUSDT", "BUY", -self.position_btc)
                if self.position_eth > 0:
                    self.order("ETHUSDT", "SELL", self.position_eth)
                elif self.position_eth < 0:
                    self.order("ETHUSDT", "BUY", -self.position_eth)
                self.position_btc = 0.0
                self.position_eth = 0.0
                self.entry_price = 0.0
                self.stop_loss = 0.0
                self.take_profit = 0.0
    
    def notify_order(self, order):
        # 可选：订单通知
        if order.status == "FILLED":
            print(f"成交: {order.symbol} {order.side} {order.quantity} @ {order.filled_avg_price}")
        elif order.status == "REJECTED":
            print(f"拒单: {order.error_msg}")
    
    def notify_trade(self, trade):
        # 可选：交易通知
        print(f"交易完成: 盈亏 {trade.pnl:.2f}, 费用 {trade.fee:.2f}")

# ==========================================
# Data Generation & Execution
# ==========================================
# ==========================================
# Real Data Fetching
# ==========================================
def fetch_real_data():
    from src.data.binance import BinanceClient
    
    client = BinanceClient()
    print("[Test] Fetching real data from Binance (30 days, 1h)...")
    
    try:
        # Fetch BTC and ETH data
        btc_bars = client.get_historical_klines("BTCUSDT", "1h", days=30)
        eth_bars = client.get_historical_klines("ETHUSDT", "1h", days=30)
        
        print(f"[Test] Fetched {len(btc_bars)} BTC bars")
        print(f"[Test] Fetched {len(eth_bars)} ETH bars")
        
        return btc_bars, eth_bars
    except Exception as e:
        print(f"[ERROR] Failed to fetch data: {e}")
        return [], []

if __name__ == "__main__":
    # Fetch Real Data
    btc_bars, eth_bars = fetch_real_data()
    
    if not btc_bars or not eth_bars:
        print("[ERROR] No data to run backtest.")
        sys.exit(1)
    
    feed = MultiFeed({
        "BTCUSDT": SingleFeed(btc_bars, "BTCUSDT"),
        "ETHUSDT": SingleFeed(eth_bars, "ETHUSDT")
    })
    
    # Get strategy code string
    strategy_code = inspect.getsource(Strategy)
    
    print("[Test] Running BacktestEngine...")
    engine = BacktestEngine(enable_logging=False) # Reduce noise
    try:
        result = engine.run(strategy_code, feed)
        
        print("\n" + "="*30)
        print("       BACKTEST REPORT       ")
        print("="*30)
        print(f"Win Rate:       {result.win_rate:.2%}")
        print(f"Total Return:   {result.total_return:.2%}")
        print(f"Sharpe Ratio:   {result.sharpe_ratio:.2f}")
        print(f"Max Drawdown:   {result.max_drawdown:.2%}")
        print("="*30)
        
    except Exception as e:
        print(f"[ERROR] Backtest failed: {e}")
        import traceback
        traceback.print_exc()
