"""Binance API 客户端"""

import requests
from typing import List, Optional

from .models import Bar


class BinanceClient:
    """Binance 数据客户端
    
    用于获取 Binance 交易所的 K 线数据。
    
    Example:
        >>> client = BinanceClient()
        >>> bars = client.get_klines("BTCUSDT", "1h", limit=100)
    """
    
    BASE_URL = "https://api.binance.com/api/v3"
    
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
            requests.HTTPError: API 请求失败
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
        
        response = requests.get(f"{self.BASE_URL}/klines", params=params)
        
        if response.status_code == 400:
            error = response.json()
            if error.get("code") == -1121:
                raise ValueError(f"无效的交易对: {symbol}")
        
        response.raise_for_status()
        
        return self._parse_klines(response.json())
    
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
