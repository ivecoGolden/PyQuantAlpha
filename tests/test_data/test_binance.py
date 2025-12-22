# tests/test_data/test_binance.py
"""BinanceClient 单元测试"""

import pytest
from unittest.mock import patch, Mock

from src.data import BinanceClient, Bar, BaseExchangeClient
from src.messages.errorMessage import ExchangeType


class TestBinanceClientInheritance:
    """测试 BinanceClient 继承关系"""
    
    def test_inherits_from_base_exchange_client(self):
        """测试继承自 BaseExchangeClient"""
        client = BinanceClient()
        assert isinstance(client, BaseExchangeClient)
    
    def test_has_default_timeout(self):
        """测试默认超时时间"""
        client = BinanceClient()
        assert client._timeout == 10
    
    def test_custom_timeout(self):
        """测试自定义超时时间"""
        client = BinanceClient(timeout=30)
        assert client._timeout == 30


class TestBinanceClientGetKlines:
    """测试 get_klines 方法"""
    
    @pytest.fixture
    def client(self):
        return BinanceClient()
    
    @pytest.fixture
    def mock_kline_data(self):
        """模拟 Binance API 返回的 K 线数据 (全部 11 字段)"""
        return [
            [1609459200000, "29000.0", "29500.0", "28800.0", "29300.0", "1000.0",
             1609462799999, "29300000.0", 5000, "600.0", "17580000.0"],
            [1609462800000, "29300.0", "29800.0", "29100.0", "29600.0", "1200.0",
             1609466399999, "35520000.0", 6000, "720.0", "21312000.0"],
        ]
    
    @patch("src.data.binance.requests.get")
    def test_get_klines_success(self, mock_get, client, mock_kline_data):
        """测试成功获取 K 线数据"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.ok = True
        mock_response.json.return_value = mock_kline_data
        mock_get.return_value = mock_response
        
        bars = client.get_klines("BTCUSDT", "1h", limit=2)
        
        assert len(bars) == 2
        assert all(isinstance(bar, Bar) for bar in bars)
        assert bars[0].close == 29300.0
        assert bars[1].close == 29600.0
    
    @patch("src.data.binance.requests.get")
    def test_get_klines_with_time_range(self, mock_get, client, mock_kline_data):
        """测试带时间范围的请求"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.ok = True
        mock_response.json.return_value = mock_kline_data
        mock_get.return_value = mock_response
        
        client.get_klines(
            "BTCUSDT", "1h",
            start_time=1609459200000,
            end_time=1609462800000
        )
        
        call_args = mock_get.call_args
        params = call_args.kwargs.get("params") or call_args[1].get("params")
        assert params["startTime"] == 1609459200000
        assert params["endTime"] == 1609462800000
    
    @patch("src.data.binance.requests.get")
    def test_limit_capped_at_1000(self, mock_get, client, mock_kline_data):
        """测试 limit 上限为 1000"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.ok = True
        mock_response.json.return_value = mock_kline_data
        mock_get.return_value = mock_response
        
        client.get_klines("BTCUSDT", "1h", limit=2000)
        
        call_args = mock_get.call_args
        params = call_args.kwargs.get("params") or call_args[1].get("params")
        assert params["limit"] == 1000


class TestBinanceClientErrorHandling:
    """测试错误处理"""
    
    @pytest.fixture
    def client(self):
        return BinanceClient()
    
    @patch("src.data.binance.requests.get")
    def test_invalid_symbol_raises_value_error(self, mock_get, client):
        """测试无效交易对抛出 ValueError"""
        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.json.return_value = {"code": -1121, "msg": "Invalid symbol"}
        mock_get.return_value = mock_response
        
        with pytest.raises(ValueError) as exc_info:
            client.get_klines("INVALID", "1h")
        
        assert "无效的交易对" in str(exc_info.value)
        assert "INVALID" in str(exc_info.value)
    
    @patch("src.data.binance.requests.get")
    def test_api_error_raises_runtime_error(self, mock_get, client):
        """测试 API 错误抛出 RuntimeError"""
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.ok = False
        mock_get.return_value = mock_response
        
        with pytest.raises(RuntimeError) as exc_info:
            client.get_klines("BTCUSDT", "1h")
        
        assert "API 请求失败" in str(exc_info.value)
        assert "500" in str(exc_info.value)
    
    @patch("src.data.binance.requests.get")
    def test_empty_data_raises_value_error(self, mock_get, client):
        """测试空数据抛出 ValueError"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.ok = True
        mock_response.json.return_value = []
        mock_get.return_value = mock_response
        
        with pytest.raises(ValueError) as exc_info:
            client.get_klines("BTCUSDT", "1h")
        
        assert "返回数据为空" in str(exc_info.value)
    
    @patch("src.data.binance.requests.get")
    def test_timeout_raises_timeout_error(self, mock_get, client):
        """测试超时抛出 TimeoutError"""
        from requests.exceptions import Timeout
        mock_get.side_effect = Timeout("Connection timed out")
        
        with pytest.raises(TimeoutError) as exc_info:
            client.get_klines("BTCUSDT", "1h")
        
        assert "请求超时" in str(exc_info.value)
    
    @patch("src.data.binance.requests.get")
    def test_network_error_raises_connection_error(self, mock_get, client):
        """测试网络错误抛出 ConnectionError"""
        from requests.exceptions import ConnectionError as ReqConnectionError
        mock_get.side_effect = ReqConnectionError("Connection refused")
        
        with pytest.raises(ConnectionError) as exc_info:
            client.get_klines("BTCUSDT", "1h")
        
        assert "网络连接失败" in str(exc_info.value)


class TestBar:
    """测试 Bar 数据模型"""
    
    def test_bar_creation(self):
        """测试 Bar 创建"""
        bar = Bar(
            timestamp=1609459200000,
            open=29000.0,
            high=29500.0,
            low=28800.0,
            close=29300.0,
            volume=1000.0
        )
        
        assert bar.timestamp == 1609459200000
        assert bar.open == 29000.0
        assert bar.high == 29500.0
        assert bar.low == 28800.0
        assert bar.close == 29300.0
        assert bar.volume == 1000.0
    
    def test_bar_is_dataclass(self):
        """测试 Bar 是 dataclass"""
        from dataclasses import is_dataclass
        assert is_dataclass(Bar)


class TestBinanceClientChainSyntax:
    """测试链式语法"""
    
    def test_chain_returns_self(self):
        """测试链式方法返回 self"""
        client = BinanceClient()
        assert client.symbol("BTCUSDT") is client
        assert client.interval("1h") is client
        assert client.limit(100) is client
        assert client.timeout(30) is client
    
    def test_chain_time_range(self):
        """测试 time_range 方法"""
        client = BinanceClient()
        client.time_range(start=1609459200000, end=1609545600000)
        assert client._start_time == 1609459200000
        assert client._end_time == 1609545600000
    
    def test_fetch_without_symbol_raises_error(self):
        """测试未设置 symbol 时 fetch 抛出异常"""
        client = BinanceClient().interval("1h")
        with pytest.raises(ValueError, match="symbol"):
            client.fetch()
    
    def test_fetch_without_interval_raises_error(self):
        """测试未设置 interval 时 fetch 抛出异常"""
        client = BinanceClient().symbol("BTCUSDT")
        with pytest.raises(ValueError, match="interval"):
            client.fetch()
    
    @patch("src.data.binance.requests.get")
    def test_chain_fetch_success(self, mock_get):
        """测试链式调用 fetch 成功"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.ok = True
        mock_response.json.return_value = [
            [1609459200000, "29000.0", "29500.0", "28800.0", "29300.0", "1000.0",
             1609462799999, "29300000.0", 5000, "600.0", "17580000.0"],
        ]
        mock_get.return_value = mock_response
        
        bars = (
            BinanceClient()
            .symbol("BTCUSDT")
            .interval("1h")
            .limit(1)
            .fetch()
        )
        
        assert len(bars) == 1
        assert bars[0].close == 29300.0
    
    @patch("src.data.binance.requests.get")
    def test_chain_with_time_range(self, mock_get):
        """测试链式调用带时间范围"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.ok = True
        mock_response.json.return_value = [
            [1609459200000, "29000.0", "29500.0", "28800.0", "29300.0", "1000.0",
             1609462799999, "29300000.0", 5000, "600.0", "17580000.0"],
        ]
        mock_get.return_value = mock_response
        
        (
            BinanceClient()
            .symbol("BTCUSDT")
            .interval("1h")
            .time_range(start=1609459200000, end=1609545600000)
            .fetch()
        )
        
        call_args = mock_get.call_args
        params = call_args.kwargs.get("params") or call_args[1].get("params")
        assert params["startTime"] == 1609459200000
        assert params["endTime"] == 1609545600000


class TestBinanceClientRetry:
    """测试重试机制"""
    
    @pytest.fixture
    def client(self):
        return BinanceClient()
    
    @patch("src.data.binance.time.sleep")
    @patch("src.data.binance.requests.get")
    def test_rate_limit_429_retries(self, mock_get, mock_sleep, client):
        """测试 429 频率限制自动重试"""
        mock_response_429 = Mock()
        mock_response_429.status_code = 429
        mock_response_429.headers = {"Retry-After": "0"}
        
        mock_response_ok = Mock()
        mock_response_ok.status_code = 200
        mock_response_ok.ok = True
        mock_response_ok.json.return_value = [
            [1609459200000, "29000.0", "29500.0", "28800.0", "29300.0", "1000.0",
             1609462799999, "29300000.0", 5000, "600.0", "17580000.0"],
        ]
        
        # 第一次返回 429，第二次成功
        mock_get.side_effect = [mock_response_429, mock_response_ok]
        
        bars = client.get_klines("BTCUSDT", "1h", limit=1)
        
        assert len(bars) == 1
        assert mock_get.call_count == 2
    
    @patch("src.data.binance.time.sleep")
    @patch("src.data.binance.requests.get")
    def test_rate_limit_429_max_retries_exceeded(self, mock_get, mock_sleep, client):
        """测试 429 超过最大重试次数抛出异常"""
        mock_response = Mock()
        mock_response.status_code = 429
        mock_response.headers = {"Retry-After": "0"}
        
        mock_get.return_value = mock_response
        
        with pytest.raises(RuntimeError) as exc_info:
            client.get_klines("BTCUSDT", "1h", limit=1)
        
        assert "请求过于频繁" in str(exc_info.value)
    
    @patch("src.data.binance.requests.get")
    def test_ip_banned_418_raises_error(self, mock_get, client):
        """测试 418 IP 封禁抛出异常"""
        mock_response = Mock()
        mock_response.status_code = 418
        mock_get.return_value = mock_response
        
        with pytest.raises(RuntimeError) as exc_info:
            client.get_klines("BTCUSDT", "1h", limit=1)
        
        assert "IP 已被封禁" in str(exc_info.value)


class TestBinanceClientHistoricalKlines:
    """测试批量历史数据获取"""
    
    @pytest.fixture
    def client(self):
        return BinanceClient()
    
    def test_invalid_interval_raises_error(self, client):
        """测试无效时间周期抛出异常"""
        with pytest.raises(ValueError) as exc_info:
            client.get_historical_klines("BTCUSDT", "invalid", days=1)
        
        assert "无效的时间周期" in str(exc_info.value)
    
    @patch("src.data.binance.time.time")
    @patch("src.data.binance.time.sleep")
    @patch("src.data.binance.requests.get")
    def test_historical_klines_single_batch(self, mock_get, mock_sleep, mock_time, client):
        """测试单批次获取历史数据"""
        # 模拟当前时间为 2021-01-02 00:00:00 UTC
        mock_time.return_value = 1609545600.0
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.ok = True
        mock_response.json.return_value = [
            [1609459200000, "29000.0", "29500.0", "28800.0", "29300.0", "1000.0",
             1609545599999, "29300000.0", 5000, "600.0", "17580000.0"],
        ]
        mock_get.return_value = mock_response
        
        bars = client.get_historical_klines("BTCUSDT", "1d", days=1)
        
        assert len(bars) >= 1
        assert all(isinstance(bar, Bar) for bar in bars)
    
    @patch("src.data.binance.time.time")
    @patch("src.data.binance.time.sleep")
    @patch("src.data.binance.requests.get")
    def test_historical_klines_multiple_batches(self, mock_get, mock_sleep, mock_time, client):
        """测试多批次获取历史数据"""
        # batch1: 1000 条，每条 1h
        # batch2: 100 条，每条 1h
        # batch2 最后一条时间戳: 1609459200000 + 1099*3600000 = 1609459200000 + 3956400000
        # 设置当前时间刚好让 batch2 最后一条的下一个时间点 >= now_ms
        base_ts = 1609459200000  # 2021-01-01 00:00:00 UTC in ms
        batch2_last_ts = base_ts + 1099 * 3600000  # 最后一条时间戳
        # 设置 now_ms = batch2_last_ts + interval_ms，这样循环会在 batch2 后终止
        fixed_now = (batch2_last_ts + 3600000) / 1000.0  # 转换为秒
        mock_time.return_value = fixed_now
        
        batch1 = [[base_ts + i * 3600000, "29000.0", "29500.0", "28800.0", "29300.0", "1000.0",
                   base_ts + i * 3600000 + 3599999, "29300000.0", 5000, "600.0", "17580000.0"]
                  for i in range(1000)]
        batch2 = [[base_ts + (1000 + i) * 3600000, "29100.0", "29600.0", "29000.0", "29400.0", "1100.0",
                   base_ts + (1000 + i) * 3600000 + 3599999, "32340000.0", 5500, "660.0", "19536000.0"]
                  for i in range(100)]
        
        mock_response1 = Mock()
        mock_response1.status_code = 200
        mock_response1.ok = True
        mock_response1.json.return_value = batch1
        
        mock_response2 = Mock()
        mock_response2.status_code = 200
        mock_response2.ok = True
        mock_response2.json.return_value = batch2
        
        mock_get.side_effect = [mock_response1, mock_response2]
        
        # 请求足够多天数覆盖 1100 条 1h 数据 (约 46 天)
        bars = client.get_historical_klines("BTCUSDT", "1h", days=50)
        
        # 应该获取到 1100 条 (1000 + 100)
        assert len(bars) == 1100

