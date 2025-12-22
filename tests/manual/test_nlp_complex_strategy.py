import asyncio
import sys
import os
import uvicorn
from unittest.mock import MagicMock
from fastapi.testclient import TestClient
from httpx import AsyncClient, ASGITransport

# Ensure src is in path
sys.path.append(os.getcwd())

from src.api.main import app
from src.api.routes.klines import get_binance_client
from src.api.routes.strategy import get_llm_dependency
from src.data import Bar
from src.ai.base import LLMResponse

# 1. Define the Complex Strategy Code (No imports, relies on injected globals)
COMPLEX_STRATEGY_CODE = '''class Strategy:
    """
    Pair Trading Strategy (BTC/ETH)
    - Uses Bollinger Bands and RSI on the spread
    - Hedges exposure
    """
    def init(self):
        # Indicators for BTC
        self.bb_btc = BollingerBands(period=20, std_dev=2.0)
        self.rsi_btc = RSI(period=14)
        self.atr_btc = ATR(period=14)
        
        # Indicators for ETH
        self.bb_eth = BollingerBands(period=20, std_dev=2.0)
        self.rsi_eth = RSI(period=14)
        self.atr_eth = ATR(period=14)
        
        # Spread Indicators
        self.spread_bb = BollingerBands(period=20, std_dev=2.0)
        self.spread_rsi = RSI(period=14)
        
        # Params
        self.hedge_ratio = 14.0
        self.position_btc = 0.0
        self.entry_price = 0.0
        self.stop_loss = 0.0
        self.take_profit = 0.0
        self.max_position = 0.1 # BTC

    def on_bar(self, bars):
        if "BTCUSDT" not in bars or "ETHUSDT" not in bars:
            return
            
        bar_btc = bars["BTCUSDT"]
        bar_eth = bars["ETHUSDT"]
        
        # Update components
        self.bb_btc.update(bar_btc.close)
        self.rsi_btc.update(bar_btc.close)
        atr_btc = self.atr_btc.update(bar_btc.high, bar_btc.low, bar_btc.close)
        
        self.bb_eth.update(bar_eth.close)
        self.rsi_eth.update(bar_eth.close)
        atr_eth = self.atr_eth.update(bar_eth.high, bar_eth.low, bar_eth.close)
        
        # Ensure sufficient history
        if not atr_btc or not atr_eth:
            return

        # Calculate Spread
        spread = bar_btc.close - bar_eth.close * self.hedge_ratio
        
        # Update Spread Indicators
        spread_bb = self.spread_bb.update(spread)
        spread_rsi = self.spread_rsi.update(spread)
        
        if not spread_bb or not spread_rsi:
            return
            
        avg_atr = (atr_btc + atr_eth * self.hedge_ratio) / 2.0
        
        # Entry Logic
        if self.position_btc == 0:
            # Short Spread: Spread > Upper Band & RSI > 70
            if spread > spread_bb.upper and spread_rsi > 70:
                self.order("BTCUSDT", "SELL", self.max_position)
                self.order("ETHUSDT", "BUY", self.max_position * self.hedge_ratio)
                self.position_btc = -self.max_position
                self.entry_price = spread
                self.stop_loss = spread + 2.0 * avg_atr
                self.take_profit = spread - 3.0 * avg_atr
                print(f"[Signal] Short Spread @ {spread:.2f}")
                
            # Long Spread: Spread < Lower Band & RSI < 30
            elif spread < spread_bb.lower and spread_rsi < 30:
                self.order("BTCUSDT", "BUY", self.max_position)
                self.order("ETHUSDT", "SELL", self.max_position * self.hedge_ratio)
                self.position_btc = self.max_position
                self.entry_price = spread
                self.stop_loss = spread - 2.0 * avg_atr
                self.take_profit = spread + 3.0 * avg_atr
                print(f"[Signal] Long Spread @ {spread:.2f}")

        # Exit Logic
        else:
            should_close = False
            # Check SL/TP
            if self.position_btc < 0: # Short Spread
                if spread >= self.stop_loss: should_close = True # Hit SL
                elif spread <= self.take_profit: should_close = True # Hit TP
            else: # Long Spread
                if spread <= self.stop_loss: should_close = True # Hit SL
                elif spread >= self.take_profit: should_close = True # Hit TP
                
            if should_close:
                if self.position_btc > 0:
                    self.close("BTCUSDT")
                    self.close("ETHUSDT")
                else:
                    self.close("BTCUSDT")
                    self.close("ETHUSDT")
                self.position_btc = 0
                print(f"[Signal] Close Position @ {spread:.2f}")
'''

# 2. Setup Mocks
mock_llm = MagicMock()
mock_binance = MagicMock()

def override_llm():
    return mock_llm

def override_binance():
    return mock_binance

# 3. Main Async Execution
async def main():
    print("🚀 [Test] Starting NLP Complex Strategy Test...")
    
    # 3.1 Setup Dependencies
    app.dependency_overrides[get_llm_dependency] = override_llm
    app.dependency_overrides[get_binance_client] = override_binance
    
    # Mock LLM Response
    mock_llm.unified_chat.return_value = LLMResponse(
        type="strategy",
        content="Here is a pair trading strategy...", # Explanation goes here for now
        code=COMPLEX_STRATEGY_CODE,
        symbols=["BTCUSDT", "ETHUSDT"]
    )
    
    # Mock Market Data (Generate Synthetic Data with correlation)
    print("📊 [Test] Generating synthetic market data...")
    btc_data = []
    eth_data = []
    base_btc = 50000.0
    base_eth = 3570.0 # ~1/14 of BTC
    
    for i in range(500):
        # Random walk
        change = (os.urandom(1)[0] / 255.0 - 0.5) * 0.02
        base_btc *= (1 + change)
        
        # ETH follows BTC but with noise (divergence)
        noise = (os.urandom(1)[0] / 255.0 - 0.5) * 0.005
        base_eth = base_btc / 14.0 * (1 + noise)
        
        ts = 1600000000000 + i * 3600000
        btc_data.append(Bar(ts, base_btc, base_btc*1.01, base_btc*0.99, base_btc, 100))
        eth_data.append(Bar(ts, base_eth, base_eth*1.01, base_eth*0.99, base_eth, 1000))

    mock_binance.get_klines.side_effect = lambda s, **k: btc_data if s == "BTCUSDT" else eth_data
    
    # 3.2 Initialize Client
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        
        # 3.3 Step 1: Chat Request
        print("💬 [Step 1] Sending natural language request...")
        chat_res = await client.post("/api/chat", json={
            "message": "Generate a complex pair trading strategy for BTC and ETH using Bollinger Bands on the spread."
        })
        
        if chat_res.status_code != 200:
            print(f"❌ Chat request failed: {chat_res.text}")
            return
            
        data = chat_res.json()
        print(f"✅ Received Strategy: {data['type']}")
        if not data['is_valid']:
            print(f"❌ Strategy Validation Failed: {data.get('error')}")
            return
            
        strategy_code = data['content']
        # print(f"Strategy Code:\n{strategy_code[:200]}...")
        
        # 3.4 Step 2: Run Backtest
        print("🏃 [Step 2] Running Backtest (30 days, 1h)...")
        run_res = await client.post("/api/backtest/run", json={
            "code": strategy_code,
            "symbol": "BTCUSDT,ETHUSDT", # Multi-asset support key
            "interval": "1h",
            "days": 30
        })
        
        if run_res.status_code != 200:
            print(f"❌ Backtest start failed: {run_res.text}")
            return
            
        task_id = run_res.json()["task_id"]
        print(f"✅ Backtest Started. Task ID: {task_id}")
        
        # 3.5 Step 3: Stream Results
        print("📡 [Step 3] Streaming results...")
        async with client.stream("GET", f"/api/backtest/stream/{task_id}") as response:
            async for line in response.aiter_lines():
                if not line: continue
                if "error" in line.lower() and "event: error" in line:
                    print(f"❌ Stream Error: {line}")
                if "total_return" in line:
                    print(f"🎉 Result: {line}")
                    break
                    
    print("✅ Test Completed Successfully")

if __name__ == "__main__":
    asyncio.run(main())
