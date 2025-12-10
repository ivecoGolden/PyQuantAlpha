# src/messages/errorMessage.py
"""错误消息与交易所类型枚举 - 支持链式语法"""

from __future__ import annotations
from enum import Enum
from typing import Final


class ExchangeType(Enum):
    """交易所类型枚举 - 用于错误消息前缀
    
    扩展方式：添加新交易所只需增加一行枚举值
    """
    BINANCE = "BinanceClient"
    OKX = "OKXClient"
    BYBIT = "BybitClient"
    HUOBI = "HuobiClient"
    GATE = "GateClient"


class MessageBuilder:
    """消息构建器 - 支持链式调用
    
    Example:
        >>> msg = MessageBuilder("无效的交易对。symbol={symbol}").exchange(ExchangeType.BINANCE).build(symbol="XXX")
        >>> print(msg)
        BinanceClient: 无效的交易对。symbol=XXX
    """
    
    def __init__(self, template: str) -> None:
        self._template = template
        self._exchange: ExchangeType | None = None
    
    def exchange(self, ex: ExchangeType) -> MessageBuilder:
        """设置交易所类型"""
        self._exchange = ex
        return self
    
    def build(self, **kwargs) -> str:
        """构建最终消息
        
        Args:
            **kwargs: 模板变量
            
        Returns:
            格式化后的完整错误消息
            
        Raises:
            ValueError: 未设置交易所类型时抛出
        """
        if self._exchange is None:
            raise ValueError("必须先调用 .exchange() 设置交易所类型")
        return f"{self._exchange.value}: {self._template.format(**kwargs)}"
    
    def __str__(self) -> str:
        """直接转字符串（用于无参数模板）"""
        if self._exchange is None:
            return self._template
        return f"{self._exchange.value}: {self._template}"


class ErrorMessage:
    """数据层错误消息模板
    
    支持两种使用方式:
    
    1. 链式语法 (推荐):
        >>> ErrorMessage.INVALID_SYMBOL.exchange(ExchangeType.BINANCE).build(symbol="XXX")
        'BinanceClient: 无效的交易对。symbol=XXX'
        
    2. 静态方法 (兼容旧代码):
        >>> ErrorMessage.format(ErrorMessage.INVALID_SYMBOL, ExchangeType.BINANCE, symbol="XXX")
        'BinanceClient: 无效的交易对。symbol=XXX'
    """
    
    # API 请求相关
    INVALID_SYMBOL: Final[MessageBuilder] = MessageBuilder("无效的交易对。symbol={symbol}")
    API_FAILED: Final[MessageBuilder] = MessageBuilder("API 请求失败。status={status}")
    EMPTY_DATA: Final[MessageBuilder] = MessageBuilder("返回数据为空")
    RATE_LIMITED: Final[MessageBuilder] = MessageBuilder("请求过于频繁，请稍后重试")
    
    # 网络相关
    NETWORK_ERROR: Final[MessageBuilder] = MessageBuilder("网络连接失败。error={error}")
    TIMEOUT: Final[MessageBuilder] = MessageBuilder("请求超时。timeout={timeout}s")
    
    # 数据解析相关
    PARSE_ERROR: Final[MessageBuilder] = MessageBuilder("数据解析失败。error={error}")
    INVALID_RESPONSE: Final[MessageBuilder] = MessageBuilder("响应格式无效")
    
    @staticmethod
    def format(template: MessageBuilder | str, exchange: ExchangeType, **kwargs) -> str:
        """格式化错误消息（兼容旧 API）
        
        Args:
            template: 错误模板 (MessageBuilder 或 str)
            exchange: 交易所类型枚举
            **kwargs: 模板变量
            
        Returns:
            格式化后的完整错误消息
        """
        tpl = template._template if isinstance(template, MessageBuilder) else template
        return f"{exchange.value}: {tpl.format(**kwargs)}"
