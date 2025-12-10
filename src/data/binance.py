# src/data/binance.py
"""Binance API 客户端 - 支持链式语法"""

from __future__ import annotations
import time
import requests
from requests.exceptions import RequestException, Timeout
from typing import List, Optional

from .base import BaseExchangeClient
from .models import Bar
from src.messages.errorMessage import ErrorMessage, ExchangeType


# 时间周期到毫秒的映射
INTERVAL_MS = {
    "1m": 60 * 1000,
    "3m": 3 * 60 * 1000,
    "5m": 5 * 60 * 1000,
    "15m": 15 * 60 * 1000,
    "30m": 30 * 60 * 1000,
    "1h": 60 * 60 * 1000,
    "2h": 2 * 60 * 60 * 1000,
    "4h": 4 * 60 * 60 * 1000,
    "6h": 6 * 60 * 60 * 1000,
    "8h": 8 * 60 * 60 * 1000,
    "12h": 12 * 60 * 60 * 1000,
    "1d": 24 * 60 * 60 * 1000,
    "3d": 3 * 24 * 60 * 60 * 1000,
    "1w": 7 * 24 * 60 * 60 * 1000,
    "1M": 30 * 24 * 60 * 60 * 1000,
}


class BinanceClient(BaseExchangeClient):
    """Binance 数据客户端 - 支持链式语法
    
    支持两种使用方式:
    
    1. 传统方式:
        >>> client = BinanceClient()
        >>> bars = client.get_klines("BTCUSDT", "1h", limit=100)
        
    2. 链式语法:
        >>> bars = (
        ...     BinanceClient()
        ...     .symbol("BTCUSDT")
        ...     .interval("1h")
        ...     .limit(100)
        ...     .fetch()
        ... )
    """
    
    BASE_URL = "https://api.binance.com/api/v3"
    DEFAULT_TIMEOUT = 10  # 秒
    MAX_RETRIES = 3       # 最大重试次数
    RETRY_DELAY = 1.0     # 基础重试延迟（秒）
    
    def __init__(self, timeout: int = DEFAULT_TIMEOUT) -> None:
        """初始化客户端"""
        self._timeout = timeout
        # 链式调用状态
        self._symbol: Optional[str] = None
        self._interval: Optional[str] = None
        self._start_time: Optional[int] = None
        self._end_time: Optional[int] = None
        self._limit: int = 500
    
    # ============ 链式配置方法 ============
    
    def symbol(self, symbol: str) -> BinanceClient:
        """设置交易对"""
        self._symbol = symbol
        return self
    
    def interval(self, interval: str) -> BinanceClient:
        """设置时间周期"""
        self._interval = interval
        return self
    
    def time_range(
        self,
        start: Optional[int] = None,
        end: Optional[int] = None
    ) -> BinanceClient:
        """设置时间范围
        
        Args:
            start: 开始时间戳 (毫秒)
            end: 结束时间戳 (毫秒)
        """
        self._start_time = start
        self._end_time = end
        return self
    
    def limit(self, limit: int) -> BinanceClient:
        """设置返回数量"""
        self._limit = limit
        return self
    
    def timeout(self, timeout: int) -> BinanceClient:
        """设置超时时间"""
        self._timeout = timeout
        return self
    
    def fetch(self) -> List[Bar]:
        """执行请求获取数据（链式调用终止方法）
        
        Returns:
            K 线数据列表
            
        Raises:
            ValueError: 未设置 symbol 或 interval
        """
        if not self._symbol:
            raise ValueError("必须先调用 .symbol() 设置交易对")
        if not self._interval:
            raise ValueError("必须先调用 .interval() 设置时间周期")
        
        return self.get_klines(
            symbol=self._symbol,
            interval=self._interval,
            start_time=self._start_time,
            end_time=self._end_time,
            limit=self._limit
        )
    
    # ============ 传统 API ============
    
    def _request_with_retry(
        self,
        url: str,
        params: dict,
        max_retries: int = MAX_RETRIES
    ) -> requests.Response:
        """发送请求并处理频率限制（自动重试）
        
        Args:
            url: 请求 URL
            params: 请求参数
            max_retries: 最大重试次数
            
        Returns:
            响应对象
            
        Raises:
            TimeoutError: 请求超时
            ConnectionError: 网络连接失败
            RuntimeError: 超过最大重试次数
        """
        last_error: Optional[Exception] = None
        
        for attempt in range(max_retries):
            try:
                response = requests.get(url, params=params, timeout=self._timeout)
                
                # 处理频率限制 (429)
                if response.status_code == 429:
                    retry_after = int(response.headers.get("Retry-After", self.RETRY_DELAY))
                    if attempt < max_retries - 1:
                        time.sleep(retry_after)
                        continue
                    raise RuntimeError(
                        ErrorMessage.RATE_LIMITED.exchange(ExchangeType.BINANCE).build()
                    )
                
                # 处理 IP 封禁 (418)
                if response.status_code == 418:
                    raise RuntimeError(
                        f"{ExchangeType.BINANCE.value}: IP 已被封禁，请稍后重试"
                    )
                
                return response
                
            except Timeout:
                last_error = TimeoutError(
                    ErrorMessage.TIMEOUT.exchange(ExchangeType.BINANCE).build(timeout=self._timeout)
                )
                if attempt < max_retries - 1:
                    time.sleep(self.RETRY_DELAY * (attempt + 1))
                    continue
                raise last_error
                
            except RequestException as e:
                last_error = ConnectionError(
                    ErrorMessage.NETWORK_ERROR.exchange(ExchangeType.BINANCE).build(error=str(e))
                )
                if attempt < max_retries - 1:
                    time.sleep(self.RETRY_DELAY * (attempt + 1))
                    continue
                raise last_error
        
        # 不应该到达这里
        raise RuntimeError("超过最大重试次数")
    
    def get_klines(
        self,
        symbol: str,
        interval: str,
        start_time: Optional[int] = None,
        end_time: Optional[int] = None,
        limit: int = 500
    ) -> List[Bar]:
        """获取 K 线数据
        
        Args:
            symbol: 交易对，如 "BTCUSDT"
            interval: 时间周期，如 "1m", "1h", "1d"
            start_time: 开始时间戳 (毫秒)，可选
            end_time: 结束时间戳 (毫秒)，可选
            limit: 返回数量，默认 500，最大 1000
            
        Returns:
            K 线数据列表
            
        Raises:
            ValueError: 无效的交易对
            TimeoutError: 请求超时
            ConnectionError: 网络连接失败
            RuntimeError: API 请求失败
        """
        params = {
            "symbol": symbol,
            "interval": interval,
            "limit": min(limit, 1000)
        }
        
        if start_time:
            params["startTime"] = start_time
        if end_time:
            params["endTime"] = end_time
        
        # 发送请求（带重试）
        response = self._request_with_retry(f"{self.BASE_URL}/klines", params)
        
        # 处理 HTTP 错误
        if response.status_code == 400:
            error = response.json()
            if error.get("code") == -1121:
                raise ValueError(
                    ErrorMessage.INVALID_SYMBOL.exchange(ExchangeType.BINANCE).build(symbol=symbol)
                )
        
        if not response.ok:
            raise RuntimeError(
                ErrorMessage.API_FAILED.exchange(ExchangeType.BINANCE).build(status=response.status_code)
            )
        
        # 解析数据
        data = response.json()
        if not data:
            raise ValueError(
                str(ErrorMessage.EMPTY_DATA.exchange(ExchangeType.BINANCE))
            )
        
        return self._parse_klines(data)
    
    def get_historical_klines(
        self,
        symbol: str,
        interval: str,
        days: int
    ) -> List[Bar]:
        """批量获取历史 K 线数据
        
        自动分批请求，每批最多 1000 条数据。
        
        Args:
            symbol: 交易对，如 "BTCUSDT"
            interval: 时间周期，如 "1m", "1h", "1d"
            days: 获取最近 N 天的数据
            
        Returns:
            K 线数据列表（按时间正序）
            
        Raises:
            ValueError: 无效的交易对或时间周期
            
        Example:
            >>> client = BinanceClient()
            >>> bars = client.get_historical_klines("BTCUSDT", "1h", days=7)
            >>> print(f"获取 {len(bars)} 根 K 线")
        """
        if interval not in INTERVAL_MS:
            raise ValueError(f"无效的时间周期: {interval}")
        
        interval_ms = INTERVAL_MS[interval]
        now_ms = int(time.time() * 1000)
        start_ms = now_ms - (days * 24 * 60 * 60 * 1000)
        
        all_bars: List[Bar] = []
        current_start = start_ms
        
        while current_start < now_ms:
            # 每批最多 1000 条
            bars = self.get_klines(
                symbol=symbol,
                interval=interval,
                start_time=current_start,
                end_time=now_ms,
                limit=1000
            )
            
            if not bars:
                break
            
            all_bars.extend(bars)
            
            # 下一批从最后一条 K 线之后开始
            current_start = bars[-1].timestamp + interval_ms
            
            # 避免请求过于频繁
            if current_start < now_ms:
                time.sleep(0.1)
        
        return all_bars
    
    def _parse_klines(self, raw_data: list) -> List[Bar]:
        """解析 K 线数据"""
        return [
            Bar(
                timestamp=item[0],
                open=float(item[1]),
                high=float(item[2]),
                low=float(item[3]),
                close=float(item[4]),
                volume=float(item[5])
            )
            for item in raw_data
        ]

