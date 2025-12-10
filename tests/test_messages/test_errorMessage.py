# tests/test_messages/test_errorMessage.py
"""ErrorMessage 单元测试"""

import pytest
from src.messages.errorMessage import ErrorMessage, ExchangeType, MessageBuilder


class TestExchangeType:
    """ExchangeType 枚举测试"""
    
    def test_binance_value(self):
        """测试 Binance 枚举值"""
        assert ExchangeType.BINANCE.value == "BinanceClient"
    
    def test_okx_value(self):
        """测试 OKX 枚举值"""
        assert ExchangeType.OKX.value == "OKXClient"
    
    def test_bybit_value(self):
        """测试 Bybit 枚举值"""
        assert ExchangeType.BYBIT.value == "BybitClient"
    
    def test_all_exchanges_have_client_suffix(self):
        """测试所有交易所枚举值都以 Client 结尾"""
        for exchange in ExchangeType:
            assert exchange.value.endswith("Client")


class TestMessageBuilder:
    """MessageBuilder 构建器测试"""
    
    def test_build_with_params(self):
        """测试带参数的消息构建"""
        builder = MessageBuilder("无效的交易对。symbol={symbol}")
        result = builder.exchange(ExchangeType.BINANCE).build(symbol="XXX")
        assert result == "BinanceClient: 无效的交易对。symbol=XXX"
    
    def test_build_without_params(self):
        """测试无参数的消息构建"""
        builder = MessageBuilder("返回数据为空")
        result = builder.exchange(ExchangeType.OKX).build()
        assert result == "OKXClient: 返回数据为空"
    
    def test_build_without_exchange_is_generic(self):
        """测试未设置交易所时返回通用消息"""
        builder = MessageBuilder("测试消息")
        assert builder.build() == "测试消息"
    
    def test_chain_returns_new_instance(self):
        """测试链式调用返回新实例 (不可变性)"""
        builder = MessageBuilder("测试")
        new_builder = builder.exchange(ExchangeType.BINANCE)
        assert new_builder is not builder
        assert new_builder._exchange == ExchangeType.BINANCE
        assert builder._exchange is None
    
    def test_str_with_exchange(self):
        """测试 __str__ 方法（已设置交易所）"""
        builder = MessageBuilder("返回数据为空")
        new_builder = builder.exchange(ExchangeType.BYBIT)
        assert str(new_builder) == "BybitClient: 返回数据为空"
    
    def test_str_without_exchange(self):
        """测试 __str__ 方法（未设置交易所）"""
        builder = MessageBuilder("返回数据为空")
        assert str(builder) == "返回数据为空"


class TestMessageBuilderContext:
    """MessageBuilder 上下文功能测试"""
    
    def test_ctx_add_variable(self):
        """测试添加通用上下文变量"""
        base = MessageBuilder("Error {code}: {msg}")
        # 链式添加 context
        ctx_msg = base.ctx(code=404).ctx(msg="Not Found")
        
        # 验证结果
        assert ctx_msg.build() == "Error 404: Not Found"
        
        # 验证原始对象未变
        assert base._context == {}
        
    def test_symbol_shortcut(self):
        """测试 .symbol() 快捷方法"""
        msg = MessageBuilder("Pair: {symbol}").symbol("ETHUSDT")
        assert msg.build() == "Pair: ETHUSDT"
        assert msg._context == {"symbol": "ETHUSDT"}
        
    def test_interval_shortcut(self):
        """测试 .interval() 快捷方法"""
        msg = MessageBuilder("Timeframe: {interval}").interval("1h")
        assert msg.build() == "Timeframe: 1h"
        assert msg._context == {"interval": "1h"}
        
    def test_context_precedence(self):
        """测试上下文优先级: Build Args > Context > Template Default"""
        msg = MessageBuilder("Value: {val}").ctx(val="Context")
        
        # 1. 使用 Context
        assert msg.build() == "Value: Context"
        
        # 2. Build 参数覆盖 Context
        assert msg.build(val="Build") == "Value: Build"
        
    def test_mixed_chaining(self):
        """测试混合链式调用 (Exchange + Context)"""
        msg = MessageBuilder("Ex: {ex}, Sym: {symbol}")
        
        # 乱序调用
        result = (msg.symbol("BTC")
                     .exchange(ExchangeType.BINANCE)
                     .ctx(ex="Binance")  #这里ex是模板变量，不是ExchangeType
                     .build())
                     
        assert result == "BinanceClient: Ex: Binance, Sym: BTC"


class TestErrorMessage:
    """ErrorMessage 类测试"""
    
    # ============ 链式语法测试 ============
    
    def test_invalid_symbol_chain(self):
        """测试 INVALID_SYMBOL 链式调用"""
        result = ErrorMessage.INVALID_SYMBOL.exchange(ExchangeType.BINANCE).build(symbol="INVALID")
        assert result == "BinanceClient: 无效的交易对。symbol=INVALID"
    
    def test_api_failed_chain(self):
        """测试 API_FAILED 链式调用"""
        result = ErrorMessage.API_FAILED.exchange(ExchangeType.OKX).build(status=500)
        assert result == "OKXClient: API 请求失败。status=500"
    
    def test_empty_data_chain(self):
        """测试 EMPTY_DATA 链式调用（无参数）"""
        result = str(ErrorMessage.EMPTY_DATA.exchange(ExchangeType.BYBIT))
        assert result == "BybitClient: 返回数据为空"
    
    def test_network_error_chain(self):
        """测试 NETWORK_ERROR 链式调用"""
        result = ErrorMessage.NETWORK_ERROR.exchange(ExchangeType.HUOBI).build(error="Connection refused")
        assert result == "HuobiClient: 网络连接失败。error=Connection refused"
    
    def test_timeout_chain(self):
        """测试 TIMEOUT 链式调用"""
        result = ErrorMessage.TIMEOUT.exchange(ExchangeType.GATE).build(timeout=30)
        assert result == "GateClient: 请求超时。timeout=30s"
    
    # ============ format 静态方法测试 ============
    
    def test_format_with_message_builder(self):
        """测试 format 方法接受 MessageBuilder"""
        result = ErrorMessage.format(ErrorMessage.INVALID_SYMBOL, ExchangeType.BINANCE, symbol="TEST")
        assert result == "BinanceClient: 无效的交易对。symbol=TEST"
    
    def test_format_with_string(self):
        """测试 format 方法接受字符串"""
        result = ErrorMessage.format("自定义错误：{msg}", ExchangeType.OKX, msg="测试")
        assert result == "OKXClient: 自定义错误：测试"
    
    def test_format_no_params(self):
        """测试 format 方法无参数模板"""
        result = ErrorMessage.format(ErrorMessage.EMPTY_DATA, ExchangeType.BYBIT)
        assert result == "BybitClient: 返回数据为空"
        
    def test_format_generic_usage(self):
        """测试 format 方法通用用法 (无 Exchange)"""
        # 1. 显式 None
        res1 = ErrorMessage.format("Error {code}", None, code=500)
        assert res1 == "Error 500"
        
        # 2. 默认参数 (省略 exchange)
        # 注意: 如果不传 exchange，必须作为关键字参数传参或者保持 positional 顺序
        # 定义是 format(template, exchange=None, **kwargs)
        res2 = ErrorMessage.format("System Error", exchange=None)
        assert res2 == "System Error"
    
    # ============ 边界情况测试 ============
    
    def test_missing_format_param_raises_error(self):
        """测试缺少格式化参数时抛出 KeyError"""
        with pytest.raises(KeyError):
            ErrorMessage.INVALID_SYMBOL.exchange(ExchangeType.BINANCE).build()
    
    def test_all_error_messages_are_message_builder(self):
        """测试所有错误消息都是 MessageBuilder 类型"""
        error_attrs = [
            ErrorMessage.INVALID_SYMBOL,
            ErrorMessage.API_FAILED,
            ErrorMessage.EMPTY_DATA,
            ErrorMessage.RATE_LIMITED,
            ErrorMessage.NETWORK_ERROR,
            ErrorMessage.TIMEOUT,
            ErrorMessage.PARSE_ERROR,
            ErrorMessage.INVALID_RESPONSE,
        ]
        for attr in error_attrs:
            assert isinstance(attr, MessageBuilder)
