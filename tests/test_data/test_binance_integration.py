# tests/test_data/test_binance_integration.py
"""BinanceClient 集成测试 - 真实 API 请求

运行方式:
    pytest tests/test_data/test_binance_integration.py -v

注意:
    - 需要网络连接
    - 可能受 Binance API 限流影响
    - 建议单独运行，不在 CI 中执行
"""

import pytest
from src.data import BinanceClient, Bar


class TestBinanceClientIntegration:
    """真实 API 请求测试"""
    
    @pytest.fixture
    def client(self):
        return BinanceClient(timeout=30)
    
    # ============ 传统 API 测试 ============
    
    def test_get_klines_btcusdt_1h(self, client):
        """测试获取 BTCUSDT 1小时 K 线"""
        bars = client.get_klines("BTCUSDT", "1h", limit=5)
        
        assert len(bars) == 5
        assert all(isinstance(bar, Bar) for bar in bars)
        
        # 验证数据合理性
        for bar in bars:
            assert bar.timestamp > 0
            assert bar.open > 0
            assert bar.high >= bar.low
            assert bar.close > 0
            assert bar.volume >= 0
    
    def test_get_klines_ethusdt_1d(self, client):
        """测试获取 ETHUSDT 日线"""
        bars = client.get_klines("ETHUSDT", "1d", limit=3)
        
        assert len(bars) == 3
        assert bars[0].close > 0
    
    def test_invalid_symbol_raises_error(self, client):
        """测试无效交易对抛出异常"""
        with pytest.raises(ValueError) as exc_info:
            client.get_klines("INVALID_SYMBOL_XYZ", "1h", limit=1)
        
        assert "无效的交易对" in str(exc_info.value)
    
    # ============ 链式语法测试 ============
    
    def test_chain_syntax_btcusdt(self):
        """测试链式语法获取数据"""
        bars = (
            BinanceClient()
            .symbol("BTCUSDT")
            .interval("1h")
            .limit(3)
            .fetch()
        )
        
        assert len(bars) == 3
        assert all(isinstance(bar, Bar) for bar in bars)
        print(f"\n最新价格: {bars[-1].close}")
    
    def test_chain_with_different_intervals(self):
        """测试不同时间周期"""
        intervals = ["1m", "5m", "15m", "1h", "4h", "1d"]
        
        for interval in intervals:
            bars = (
                BinanceClient()
                .symbol("BTCUSDT")
                .interval(interval)
                .limit(1)
                .fetch()
            )
            assert len(bars) == 1, f"interval={interval} 失败"
    
    # ============ 边界测试 ============
    
    def test_limit_max_1000(self, client):
        """测试 limit 上限 1000"""
        bars = client.get_klines("BTCUSDT", "1m", limit=1000)
        assert len(bars) == 1000
    
    def test_limit_exceeds_1000_capped(self, client):
        """测试超过 1000 被限制"""
        bars = client.get_klines("BTCUSDT", "1m", limit=2000)
        assert len(bars) == 1000  # 被限制为最大值
    
    # ============ 批量历史数据测试 ============
    
    def test_historical_klines_1_day(self, client):
        """测试获取 1 天历史数据"""
        bars = client.get_historical_klines("BTCUSDT", "1h", days=1)
        
        # 1 天 = 24 小时，应该有约 24 根 K 线
        assert 20 <= len(bars) <= 25
        assert all(isinstance(bar, Bar) for bar in bars)
        print(f"\n获取 {len(bars)} 根 1h K 线")
    
    def test_historical_klines_7_days(self, client):
        """测试获取 7 天历史数据"""
        bars = client.get_historical_klines("ETHUSDT", "4h", days=7)
        
        # 7 天 * 6 根/天 = 42 根 4h K 线
        assert 35 <= len(bars) <= 45
        print(f"\n获取 {len(bars)} 根 4h K 线")
    
    def test_historical_klines_invalid_interval(self, client):
        """测试无效时间周期抛出异常"""
        with pytest.raises(ValueError) as exc_info:
            client.get_historical_klines("BTCUSDT", "invalid", days=1)
        
        assert "无效的时间周期" in str(exc_info.value)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

