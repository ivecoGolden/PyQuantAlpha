# tests/test_data/test_binance_futures.py
"""BinanceFuturesClient 测试"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import time

from src.data.binance_futures import (
    BinanceFuturesClient,
    FundingRateData,
    SentimentData,
)


class TestFundingRateData:
    """FundingRateData 数据类测试"""
    
    def test_create_funding_rate_data(self):
        """测试创建资金费率数据"""
        data = FundingRateData(
            symbol="BTCUSDT",
            timestamp=1700000000000,
            funding_rate=0.0001,
            mark_price=35000.0
        )
        assert data.symbol == "BTCUSDT"
        assert data.funding_rate == 0.0001
        assert data.mark_price == 35000.0


class TestSentimentData:
    """SentimentData 数据类测试"""
    
    def test_create_sentiment_data(self):
        """测试创建情绪数据"""
        data = SentimentData(
            symbol="BTCUSDT",
            timestamp=1700000000000,
            long_short_ratio=1.25,
            long_account_ratio=0.556,
            short_account_ratio=0.444
        )
        assert data.long_short_ratio == 1.25
        assert abs(data.long_account_ratio + data.short_account_ratio - 1.0) < 0.01


class TestBinanceFuturesClient:
    """BinanceFuturesClient 测试"""
    
    @pytest.fixture
    def client(self):
        return BinanceFuturesClient(timeout=5)
    
    def test_init(self, client):
        """测试客户端初始化"""
        assert client._timeout == 5
        assert client._max_retries == 3
        assert client.BASE_URL == "https://fapi.binance.com"
    
    @patch("src.data.binance_futures.requests.get")
    def test_get_funding_rate_history(self, mock_get, client):
        """测试获取资金费率历史"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            {
                "symbol": "BTCUSDT",
                "fundingTime": 1700000000000,
                "fundingRate": "0.00010000",
                "markPrice": "35000.00000000"
            },
            {
                "symbol": "BTCUSDT",
                "fundingTime": 1700028800000,
                "fundingRate": "0.00015000",
                "markPrice": "35100.00000000"
            }
        ]
        mock_get.return_value = mock_response
        
        rates = client.get_funding_rate_history("BTCUSDT", limit=2)
        
        assert len(rates) == 2
        assert rates[0].symbol == "BTCUSDT"
        assert rates[0].funding_rate == 0.0001
        assert rates[1].funding_rate == 0.00015
        
        mock_get.assert_called_once()
    
    @patch("src.data.binance_futures.requests.get")
    def test_get_long_short_ratio(self, mock_get, client):
        """测试获取多空比"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            {
                "symbol": "BTCUSDT",
                "timestamp": 1700000000000,
                "longShortRatio": "1.2500",
                "longAccount": "0.5556",
                "shortAccount": "0.4444"
            }
        ]
        mock_get.return_value = mock_response
        
        sentiment = client.get_long_short_ratio("BTCUSDT", "1h", limit=1)
        
        assert len(sentiment) == 1
        assert sentiment[0].long_short_ratio == 1.25
        assert sentiment[0].long_account_ratio == 0.5556
    
    @patch("src.data.binance_futures.requests.get")
    def test_request_error_handling(self, mock_get, client):
        """测试请求错误处理"""
        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.json.return_value = {"msg": "Invalid symbol"}
        mock_get.return_value = mock_response
        
        with pytest.raises(ValueError, match="获取资金费率失败"):
            client.get_funding_rate_history("INVALID")
    
    @patch("src.data.binance_futures.requests.get")
    def test_empty_response(self, mock_get, client):
        """测试空响应"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = []
        mock_get.return_value = mock_response
        
        rates = client.get_funding_rate_history("BTCUSDT", limit=10)
        assert rates == []
    
    @patch("src.data.binance_futures.requests.get")
    def test_get_long_short_ratio_no_time_params(self, mock_get, client):
        """测试 get_long_short_ratio 不传递 startTime/endTime 参数
        
        Binance API 的 globalLongShortAccountRatio 端点不支持这些参数
        """
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            {
                "symbol": "BTCUSDT",
                "timestamp": 1700000000000,
                "longShortRatio": "1.5000",
                "longAccount": "0.6000",
                "shortAccount": "0.4000"
            }
        ]
        mock_get.return_value = mock_response
        
        client.get_long_short_ratio("BTCUSDT", "4h", limit=24)
        
        # 验证调用参数不包含 startTime/endTime
        call_args = mock_get.call_args
        params = call_args.kwargs.get("params", {}) or call_args[1].get("params", {})
        assert "startTime" not in params
        assert "endTime" not in params
        assert params.get("limit") == 24
        assert params.get("period") == "4h"
