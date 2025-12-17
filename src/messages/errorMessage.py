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


class LLMType(Enum):
    """LLM 提供商类型枚举"""
    DEEPSEEK = "DeepSeek"
    OPENAI = "OpenAI"
    CLAUDE = "Claude"


class MessageBuilder:
    """消息构建器 - 支持链式调用 (不可变模式)
    
    Example:
        >>> msg = MessageBuilder("无效的交易对。symbol={symbol}").exchange(ExchangeType.BINANCE).symbol("BTCUSDT").build()
        >>> print(msg)
        BinanceClient: 无效的交易对。symbol=BTCUSDT
    """
    
    def __init__(self, template: str, exchange: ExchangeType | None = None, context: dict | None = None) -> None:
        self._template = template
        self._exchange = exchange
        self._context = context or {}
    
    def exchange(self, ex: ExchangeType) -> MessageBuilder:
        """设置交易所类型 (返回新实例)"""
        return MessageBuilder(self._template, exchange=ex, context=self._context)
        
    def ctx(self, **kwargs) -> MessageBuilder:
        """添加通用上下文变量 (返回新实例)"""
        new_context = self._context.copy()
        new_context.update(kwargs)
        return MessageBuilder(self._template, exchange=self._exchange, context=new_context)
    
    def symbol(self, value: str) -> MessageBuilder:
        """设置交易对 (ctx Shortcut)"""
        return self.ctx(symbol=value)
        
    def interval(self, value: str) -> MessageBuilder:
        """设置时间周期 (ctx Shortcut)"""
        return self.ctx(interval=value)
    
    def build(self, **kwargs) -> str:
        """构建最终消息
        
        Args:
            **kwargs: 额外的模板变量 (优先级高于 context)
            
        Returns:
            格式化后的完整错误消息
        """
        # 合并上下文: build参数 > context > template
        final_kwargs = self._context.copy()
        final_kwargs.update(kwargs)
        
        msg = self._template.format(**final_kwargs)
        
        if self._exchange:
            return f"{self._exchange.value}: {msg}"
        return msg
    
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
    
    # ============ API 请求相关 ============
    INVALID_SYMBOL: Final[MessageBuilder] = MessageBuilder("无效的交易对。symbol={symbol}")
    API_FAILED: Final[MessageBuilder] = MessageBuilder("API 请求失败。status={status}")
    EMPTY_DATA: Final[MessageBuilder] = MessageBuilder("返回数据为空")
    RATE_LIMITED: Final[MessageBuilder] = MessageBuilder("请求过于频繁，请稍后重试")
    IP_BANNED: Final[MessageBuilder] = MessageBuilder("IP 已被封禁，请稍后重试")
    MAX_RETRIES_EXCEEDED: Final[str] = "超过最大重试次数"
    
    # ============ 网络相关 ============
    NETWORK_ERROR: Final[MessageBuilder] = MessageBuilder("网络连接失败。error={error}")
    TIMEOUT: Final[MessageBuilder] = MessageBuilder("请求超时。timeout={timeout}s")
    
    # ============ 数据解析相关 ============
    PARSE_ERROR: Final[MessageBuilder] = MessageBuilder("数据解析失败。error={error}")
    INVALID_RESPONSE: Final[MessageBuilder] = MessageBuilder("响应格式无效")
    INVALID_INTERVAL: Final[str] = "无效的时间周期: {interval}"
    
    # ============ 链式语法相关 ============
    CHAIN_MISSING_SYMBOL: Final[str] = "必须先调用 .symbol() 设置交易对"
    CHAIN_MISSING_INTERVAL: Final[str] = "必须先调用 .interval() 设置时间周期"
    CHAIN_MISSING_EXCHANGE: Final[str] = "必须先调用 .exchange() 设置交易所类型"
    
    # ============ AI 相关 ============
    LLM_API_FAILED: Final[str] = "{provider} API 调用失败: {error}"
    LLM_PROVIDER_NOT_SUPPORTED: Final[str] = "不支持的 LLM 提供商: {provider}"
    LLM_PROVIDER_NOT_IMPLEMENTED: Final[str] = "{provider} 客户端尚未实现"
    LLM_INVALID_JSON: Final[str] = "LLM 返回了无效的 JSON 格式: {error}"
    
    # ============ 策略校验相关 ============
    STRATEGY_CODE_EMPTY: Final[str] = "代码不能为空"
    STRATEGY_CLASS_NOT_FOUND: Final[str] = "未找到 Strategy 类定义"
    STRATEGY_ONLY_ONE_CLASS: Final[str] = "只能定义一个 Strategy 类"
    STRATEGY_WRONG_CLASS_NAME: Final[str] = "类名必须是 Strategy，而不是 {name}"
    STRATEGY_MISSING_INIT: Final[str] = "缺少 init() 方法"
    STRATEGY_MISSING_ON_BAR: Final[str] = "缺少 on_bar() 方法"
    STRATEGY_FORBIDDEN_NODE: Final[str] = "不允许使用 {node}"
    STRATEGY_FORBIDDEN_CALL: Final[str] = "不允许调用 {func}()"
    STRATEGY_SYNTAX_ERROR: Final[str] = "语法错误: {msg} (行 {line})"
    STRATEGY_EXECUTE_FAILED: Final[str] = "策略代码执行失败: {error}"
    STRATEGY_INVALID: Final[str] = "策略代码无效: {msg}"
    STRATEGY_FORBIDDEN_IMPORT: Final[str] = "禁止引入模块: {module} (仅允许: math, random, etc.)"
    
    # ============ 回测相关 ============
    BACKTEST_DATA_EMPTY: Final[str] = "回测数据为空"
    BACKTEST_STRATEGY_INIT_FAILED: Final[str] = "策略初始化失败: {error}"
    BACKTEST_STRATEGY_ERROR: Final[str] = "策略执行异常: {error}"
    BACKTEST_INSUFFICIENT_FUNDS: Final[str] = "资金不足"
    BACKTEST_INSUFFICIENT_POSITION: Final[str] = "持仓不足"
    BACKTEST_ORDER_REJECTED: Final[str] = "订单 {order_id} 拒绝: {reason}"
    
    # ============ HTTP 相关 ============
    HTTP_INTERNAL_ERROR: Final[str] = "内部错误: {error}"
    HTTP_AI_GENERATE_FAILED: Final[str] = "AI 生成失败: {error}"
    
    @staticmethod
    def format(template: MessageBuilder | str, exchange: ExchangeType | None = None, **kwargs) -> str:
        """格式化错误消息（兼容旧 API）
        
        Args:
            template: 错误模板 (MessageBuilder 或 str)
            exchange: 交易所类型枚举 (可选)
            **kwargs: 模板变量
            
        Returns:
            格式化后的完整错误消息
        """
        tpl = template._template if isinstance(template, MessageBuilder) else template
        msg = tpl.format(**kwargs)
        
        if exchange:
            return f"{exchange.value}: {msg}"
        return msg

