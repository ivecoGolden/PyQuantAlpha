# src/data/binance_futures.py
"""Binance Futures API 客户端

用于获取合约衍生数据：
- 资金费率 (Funding Rate)
- 多空账户比 (Long/Short Ratio)
"""

from __future__ import annotations
import time
import requests
from requests.exceptions import RequestException, Timeout
from typing import List, Optional
from dataclasses import dataclass
from decimal import Decimal
import logging

from src.messages.errorMessage import ErrorMessage

logger = logging.getLogger("pyquantalpha")


@dataclass
class FundingRateData:
    """资金费率数据模型"""
    symbol: str
    timestamp: int  # fundingTime
    funding_rate: float
    mark_price: float


@dataclass
class SentimentData:
    """市场情绪数据模型"""
    symbol: str
    timestamp: int
    long_short_ratio: float
    long_account_ratio: float
    short_account_ratio: float


class BinanceFuturesClient:
    """Binance Futures API 客户端
    
    专用于获取合约市场的衍生数据，包括：
    - 资金费率历史
    - 全局多空账户比
    
    Example:
        >>> client = BinanceFuturesClient()
        >>> rates = client.get_funding_rate_history("BTCUSDT", limit=100)
        >>> sentiment = client.get_long_short_ratio("BTCUSDT", "1h", limit=24)
    """
    
    BASE_URL = "https://fapi.binance.com"
    
    def __init__(self, timeout: int = 10) -> None:
        """初始化客户端
        
        Args:
            timeout: 请求超时时间（秒）
        """
        self._timeout = timeout
        self._max_retries = 3
        self._retry_delay = 1.0
    
    def _request(self, endpoint: str, params: dict = None) -> dict | list:
        """发送 HTTP 请求
        
        Args:
            endpoint: API 端点路径
            params: 请求参数
            
        Returns:
            JSON 响应数据
            
        Raises:
            ConnectionError: 网络连接失败
            TimeoutError: 请求超时
            ValueError: API 返回错误
        """
        url = f"{self.BASE_URL}{endpoint}"
        
        for attempt in range(self._max_retries):
            try:
                response = requests.get(url, params=params, timeout=self._timeout)
                
                if response.status_code == 200:
                    return response.json()
                elif response.status_code == 400:
                    error_data = response.json()
                    raise ValueError(f"Binance Futures API 错误: {error_data.get('msg', 'Unknown')}")
                elif response.status_code == 429:
                    # 频率限制
                    retry_after = int(response.headers.get("Retry-After", 60))
                    logger.warning(f"Futures API 频率限制，等待 {retry_after}s")
                    time.sleep(retry_after)
                    continue
                else:
                    response.raise_for_status()
                    
            except Timeout:
                if attempt == self._max_retries - 1:
                    raise TimeoutError(f"Futures API 请求超时: {endpoint}")
                time.sleep(self._retry_delay)
            except RequestException as e:
                if attempt == self._max_retries - 1:
                    raise ConnectionError(f"Futures API 连接失败: {e}")
                time.sleep(self._retry_delay)
        
        raise ConnectionError("Futures API 请求失败，已达最大重试次数")
    
    def get_funding_rate_history(
        self,
        symbol: str,
        start_time: Optional[int] = None,
        end_time: Optional[int] = None,
        limit: int = 100
    ) -> List[FundingRateData]:
        """获取资金费率历史
        
        Args:
            symbol: 交易对，如 "BTCUSDT"
            start_time: 开始时间戳（毫秒）
            end_time: 结束时间戳（毫秒）
            limit: 返回数量，最大 1000
            
        Returns:
            资金费率数据列表
            
        Example:
            >>> rates = client.get_funding_rate_history("BTCUSDT", limit=10)
            >>> for r in rates:
            ...     print(f"{r.timestamp}: {r.funding_rate:.6f}")
        """
        params = {
            "symbol": symbol,
            "limit": min(limit, 1000)
        }
        if start_time:
            params["startTime"] = start_time
        if end_time:
            params["endTime"] = end_time
        
        try:
            data = self._request("/fapi/v1/fundingRate", params)
        except ValueError as e:
            # 可能是无效交易对
            raise ValueError(f"获取资金费率失败: {e}")
        
        if not data:
            return []
        
        return [
            FundingRateData(
                symbol=item["symbol"],
                timestamp=item["fundingTime"],
                funding_rate=float(item["fundingRate"]),
                mark_price=float(item.get("markPrice", 0))
            )
            for item in data
        ]
    
    def get_long_short_ratio(
        self,
        symbol: str,
        period: str = "1h",
        limit: int = 30
    ) -> List[SentimentData]:
        """获取全局多空账户比
        
        注意：Binance Futures API 的 globalLongShortAccountRatio 端点
        不支持 startTime/endTime 参数，只能通过 limit 获取最近 N 条数据。
        
        Args:
            symbol: 交易对，如 "BTCUSDT"
            period: 统计周期，可选 "5m", "15m", "30m", "1h", "2h", "4h", "6h", "12h", "1d"
            limit: 返回数量，最大 500
            
        Returns:
            市场情绪数据列表
            
        Example:
            >>> sentiment = client.get_long_short_ratio("BTCUSDT", "1h", limit=24)
            >>> for s in sentiment:
            ...     print(f"{s.timestamp}: long/short = {s.long_short_ratio:.4f}")
        """
        params = {
            "symbol": symbol,
            "period": period,
            "limit": min(limit, 500)
        }
        # 注意：不传递 startTime/endTime，该 API 不支持这些参数
        
        try:
            data = self._request("/futures/data/globalLongShortAccountRatio", params)
        except ValueError as e:
            raise ValueError(f"获取多空比失败: {e}")
        
        if not data:
            return []
        
        return [
            SentimentData(
                symbol=symbol,
                timestamp=item["timestamp"],
                long_short_ratio=float(item["longShortRatio"]),
                long_account_ratio=float(item["longAccount"]),
                short_account_ratio=float(item["shortAccount"])
            )
            for item in data
        ]
    
    def get_funding_rate_history_batch(
        self,
        symbol: str,
        days: int = 30
    ) -> List[FundingRateData]:
        """批量获取资金费率历史（自动分页）
        
        资金费率每 8 小时结算一次，所以 30 天约 90 条数据。
        
        Args:
            symbol: 交易对
            days: 获取最近 N 天的数据
            
        Returns:
            资金费率数据列表（按时间正序）
        """
        end_time = int(time.time() * 1000)
        start_time = end_time - days * 24 * 3600 * 1000
        
        all_data: List[FundingRateData] = []
        current_end = end_time
        
        while current_end > start_time:
            batch = self.get_funding_rate_history(
                symbol=symbol,
                start_time=start_time,
                end_time=current_end,
                limit=1000
            )
            
            if not batch:
                break
            
            all_data.extend(batch)
            
            # 下一批从最早一条之前开始
            current_end = min(item.timestamp for item in batch) - 1
            
            # 避免频繁请求
            time.sleep(0.1)
        
        # 按时间正序
        all_data.sort(key=lambda x: x.timestamp)
        return all_data
