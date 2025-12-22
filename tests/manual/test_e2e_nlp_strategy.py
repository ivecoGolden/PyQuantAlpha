#!/usr/bin/env python
# tests/manual/test_e2e_nlp_strategy.py
"""
端到端测试：自然语言生成复杂策略并运行回测

此脚本测试完整流程：
1. 调用真实 LLM API 生成策略
2. 验证生成的策略代码
3. 获取市场数据
4. 运行回测
5. 输出绩效指标

运行方式:
    conda activate pyquantalpha
    python tests/manual/test_e2e_nlp_strategy.py
"""

import asyncio
import os
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv
load_dotenv()


def test_e2e_nlp_strategy():
    """端到端测试：自然语言 -> 策略代码 -> 回测"""
    
    print("=" * 60)
    print("🚀 PyQuantAlpha 端到端测试：自然语言策略生成")
    print("=" * 60)
    
    # 1. 初始化 LLM 客户端
    print("\n📝 Step 1: 初始化 LLM 客户端...")
    
    from src.ai.factory import create_llm_client, LLMProvider
    
    # 选择 provider 和 api_key
    deepseek_key = os.getenv("DEEPSEEK_API_KEY")
    openai_key = os.getenv("OPENAI_API_KEY")
    
    if deepseek_key:
        provider = LLMProvider.DEEPSEEK
        api_key = deepseek_key
    elif openai_key:
        provider = LLMProvider.OPENAI
        api_key = openai_key
    else:
        print("❌ 错误：未找到 API Key")
        print("   请设置 DEEPSEEK_API_KEY 或 OPENAI_API_KEY 环境变量")
        return False
    
    print(f"   使用 LLM Provider: {provider.value}")
    
    try:
        client = create_llm_client(provider, api_key)
        print("   ✅ LLM 客户端初始化成功")
    except Exception as e:
        print(f"   ❌ LLM 客户端初始化失败: {e}")
        return False
    
    # 2. 发送自然语言请求
    print("\n📝 Step 2: 发送自然语言请求...")
    
    user_message = """生成一个复杂的策略
"""
    print(f"   用户输入: {user_message[:50]}...")
    
    try:
        # unified_chat 是同步方法
        response = client.unified_chat(user_message)
        print(f"   ✅ LLM 响应成功")
        print(f"   响应类型: {response.type}")
    except Exception as e:
        print(f"   ❌ LLM 请求失败: {e}")
        return False
    
    # 3. 验证策略代码
    print("\n📝 Step 3: 验证策略代码...")
    
    if response.type != "strategy" or not response.code:
        print(f"   ❌ 未返回策略代码，响应类型: {response.type}")
        print(f"   内容: {response.content[:200]}...")
        return False
    
    strategy_code = response.code
    print(f"   策略代码长度: {len(strategy_code)} 字符")
    
    # 显示前 20 行
    lines = strategy_code.split('\n')[:20]
    print("   策略代码预览:")
    for line in lines:
        print(f"   {line}")
    if len(strategy_code.split('\n')) > 20:
        print("   ...")
    
    from src.backtest.loader import validate_strategy_code
    
    is_valid, error_msg = validate_strategy_code(strategy_code)
    if is_valid:
        print("   ✅ 策略代码验证通过")
    else:
        print(f"   ❌ 策略代码验证失败: {error_msg}")
        return False
    
    # 4. 获取市场数据
    print("\n📝 Step 4: 获取市场数据...")
    
    from src.data.binance import BinanceClient
    
    binance = BinanceClient()
    symbol = response.symbols[0] if response.symbols else "BTCUSDT"
    
    try:
        bars = binance.get_historical_klines(symbol, "1h", days=30)
        print(f"   ✅ 获取 {symbol} 数据成功: {len(bars)} 根 K 线")
    except Exception as e:
        print(f"   ❌ 获取数据失败: {e}")
        return False
    
    if len(bars) < 100:
        print(f"   ⚠️ 数据量不足，使用 get_klines 获取")
        bars = binance.get_klines(symbol, "1h", limit=500)
        print(f"   ✅ 获取 {symbol} 数据成功: {len(bars)} 根 K 线")
    
    # 5. 运行回测
    print("\n📝 Step 5: 运行回测...")
    
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
        print("   ✅ 回测完成")
    except Exception as e:
        print(f"   ❌ 回测失败: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # 6. 输出绩效
    print("\n📊 Step 6: 回测绩效报告")
    print("=" * 60)
    print(f"📈 总收益率:     {result.total_return:.2%}")
    print(f"📈 年化收益率:   {result.annualized_return:.2%}")
    print(f"📉 最大回撤:     {result.max_drawdown:.2%}")
    print(f"📊 夏普比率:     {result.sharpe_ratio:.2f}")
    print(f"🎯 胜率:         {result.win_rate:.2%}")
    print(f"💰 盈亏比:       {result.profit_factor:.2f}")
    print(f"📊 总交易次数:   {result.total_trades}")
    print("=" * 60)
    
    # 7. 交易明细
    if result.trades:
        print("\n📋 最近 5 笔交易:")
        for trade in result.trades[-5:]:
            pnl_str = f"+{trade.pnl:.2f}" if trade.pnl >= 0 else f"{trade.pnl:.2f}"
            print(f"   {trade.symbol} {trade.side.value} {trade.quantity:.4f} @ {trade.price:.2f} | PnL: {pnl_str}")
    
    print("\n✅ 端到端测试完成！")
    return True


if __name__ == "__main__":
    success = test_e2e_nlp_strategy()
    sys.exit(0 if success else 1)

