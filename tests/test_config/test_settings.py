# tests/test_config/test_settings.py
"""Settings 配置测试"""

import pytest
import os
from unittest.mock import patch

from src.config.settings import Settings


class TestSettingsDefaults:
    """Settings 默认值测试"""
    
    def test_api_title_default(self):
        """测试 API 标题默认值"""
        settings = Settings()
        assert settings.API_TITLE == "PyQuantAlpha API"
    
    def test_api_version_default(self):
        """测试 API 版本默认值"""
        settings = Settings()
        assert settings.API_VERSION == "0.1.0"
    
    def test_api_description_default(self):
        """测试 API 描述默认值"""
        settings = Settings()
        assert "量化" in settings.API_DESCRIPTION
    
    def test_binance_timeout_default(self):
        """测试 Binance 超时默认值"""
        settings = Settings()
        assert settings.BINANCE_TIMEOUT == 10
    
    def test_binance_max_retries_default(self):
        """测试 Binance 最大重试次数默认值"""
        settings = Settings()
        assert settings.BINANCE_MAX_RETRIES == 3
    
    def test_binance_retry_delay_default(self):
        """测试 Binance 重试延迟默认值"""
        settings = Settings()
        assert settings.BINANCE_RETRY_DELAY == 1.0
    
    def test_log_level_default(self):
        """测试日志级别默认值"""
        settings = Settings()
        assert settings.LOG_LEVEL == "INFO"
    
    def test_log_json_format_default(self):
        """测试 JSON 格式日志默认值"""
        settings = Settings()
        assert settings.LOG_JSON_FORMAT is False


class TestSettingsEnvironmentOverride:
    """Settings 环境变量覆盖测试"""
    
    def test_api_version_from_env(self):
        """测试从环境变量读取 API 版本"""
        with patch.dict(os.environ, {"API_VERSION": "1.0.0"}):
            settings = Settings()
            assert settings.API_VERSION == "1.0.0"
    
    def test_binance_timeout_from_env(self):
        """测试从环境变量读取 Binance 超时"""
        with patch.dict(os.environ, {"BINANCE_TIMEOUT": "30"}):
            settings = Settings()
            assert settings.BINANCE_TIMEOUT == 30
    
    def test_log_level_from_env(self):
        """测试从环境变量读取日志级别"""
        with patch.dict(os.environ, {"LOG_LEVEL": "DEBUG"}):
            settings = Settings()
            assert settings.LOG_LEVEL == "DEBUG"
    
    def test_log_json_format_from_env(self):
        """测试从环境变量读取 JSON 格式日志"""
        with patch.dict(os.environ, {"LOG_JSON_FORMAT": "true"}):
            settings = Settings()
            assert settings.LOG_JSON_FORMAT is True


class TestSettingsTypes:
    """Settings 类型验证测试"""
    
    def test_timeout_is_int(self):
        """测试超时是整数类型"""
        settings = Settings()
        assert isinstance(settings.BINANCE_TIMEOUT, int)
    
    def test_retry_delay_is_float(self):
        """测试重试延迟是浮点类型"""
        settings = Settings()
        assert isinstance(settings.BINANCE_RETRY_DELAY, float)
    
    def test_json_format_is_bool(self):
        """测试 JSON 格式是布尔类型"""
        settings = Settings()
        assert isinstance(settings.LOG_JSON_FORMAT, bool)
