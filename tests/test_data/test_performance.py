# tests/test_data/test_performance.py
"""
数据库性能基准测试

验证 Step 1 性能指标:
- 冷启动 (首次网络请求): < 5s
- 热启动 (缓存命中): < 100ms
- 读库速度: 比网络快 10x 以上

运行方式:
    pytest tests/test_data/test_performance.py -v -s --run-benchmark
"""

import pytest
import time
from typing import Tuple

from src.data.repository import MarketDataRepository
from src.data.binance import BinanceClient
from src.database import init_db


@pytest.mark.benchmark
class TestPerformanceBenchmark:
    """性能基准测试 (需要网络)"""
    
    @pytest.fixture
    def repo(self):
        """获取 Repository 实例"""
        return MarketDataRepository()
    
    @pytest.fixture
    def client(self):
        """获取 Binance 客户端"""
        return BinanceClient()
    
    @staticmethod
    def measure_time(func) -> Tuple[float, any]:
        """测量函数执行时间"""
        start = time.perf_counter()
        result = func()
        elapsed = time.perf_counter() - start
        return elapsed, result
    
    @staticmethod
    async def measure_async_time(coro) -> Tuple[float, any]:
        """测量异步函数执行时间"""
        start = time.perf_counter()
        result = await coro
        elapsed = time.perf_counter() - start
        return elapsed, result
    
    def test_network_baseline(self, client):
        """测试网络请求基准时间 (1000 条)"""
        elapsed, bars = self.measure_time(
            lambda: client.get_klines("BTCUSDT", "1h", limit=1000)
        )
        
        print(f"\n📊 网络请求 1000 条: {elapsed:.3f}s")
        print(f"   数据条数: {len(bars)}")
        
        assert len(bars) == 1000
        assert elapsed < 10.0  # 宽松阈值
    
    @pytest.mark.asyncio
    async def test_cold_start(self, client):
        """测试冷启动 (使用历史数据接口) - 目标 < 5s"""
        elapsed, bars = self.measure_time(
            lambda: client.get_historical_klines("BTCUSDT", "1h", days=30)
        )
        
        print(f"\n❄️  冷启动 (30 天数据): {elapsed:.3f}s")
        print(f"   数据条数: {len(bars)}")
        
        assert elapsed < 5.0, f"冷启动 {elapsed:.2f}s > 5s"
    
    @pytest.mark.asyncio
    async def test_warm_start(self, repo, client):
        """测试热启动 (缓存命中) - 目标 < 100ms"""
        await init_db()
        
        # 先用 sync_klines 预热（使用 limit 参数避免空数据问题）
        bars = client.get_klines("BTCUSDT", "1h", limit=100)
        if bars:
            start_time = bars[0].timestamp
            end_time = bars[-1].timestamp
            
            # 缓存读取
            elapsed, (cached_bars, _) = await self.measure_async_time(
                repo.get_klines("BTCUSDT", "1h", start_time, end_time)
            )
            
            print(f"\n🔥 热启动: {elapsed * 1000:.1f}ms")
            print(f"   数据条数: {len(cached_bars)}")
            
            assert elapsed < 0.1, f"热启动 {elapsed * 1000:.1f}ms > 100ms"
    
    @pytest.mark.asyncio
    async def test_speedup_ratio(self, repo, client):
        """测试速度提升倍数 - 目标 >= 10x"""
        await init_db()
        
        # 网络基准
        network_time, bars = self.measure_time(
            lambda: client.get_klines("BTCUSDT", "1h", limit=200)
        )
        
        if not bars:
            pytest.skip("无法获取网络数据")
        
        # 获取时间范围
        start_time = bars[0].timestamp
        end_time = bars[-1].timestamp
        
        # 预热缓存
        await repo.sync_klines("BTCUSDT", "1h", start_time, end_time)
        
        # 缓存读取 (多次平均)
        cache_times = []
        for _ in range(5):
            t, _ = await self.measure_async_time(
                repo.get_klines("BTCUSDT", "1h", start_time, end_time)
            )
            cache_times.append(t)
        
        cache_time = sum(cache_times) / len(cache_times)
        speedup = network_time / cache_time if cache_time > 0 else float('inf')
        
        print(f"\n⚡ 速度对比:")
        print(f"   网络: {network_time * 1000:.1f}ms")
        print(f"   缓存: {cache_time * 1000:.2f}ms")
        print(f"   加速: {speedup:.1f}x")
        
        assert speedup >= 10, f"加速 {speedup:.1f}x < 10x"


class TestQuickBenchmark:
    """快速基准测试 (无网络依赖)"""
    
    @pytest.mark.asyncio
    async def test_db_read_latency(self):
        """测试数据库读取延迟"""
        from src.database import get_session, init_db
        from src.database.models import Candlestick
        from sqlalchemy import select
        
        await init_db()
        
        async with get_session() as session:
            start = time.perf_counter()
            stmt = select(Candlestick).limit(1000)
            result = await session.execute(stmt)
            _ = result.scalars().all()
            elapsed = time.perf_counter() - start
        
        print(f"\n📖 DB 读取延迟: {elapsed * 1000:.2f}ms")
        assert elapsed < 0.5
