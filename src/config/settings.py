from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional

class Settings(BaseSettings):
    """应用配置"""
    
    # API 配置
    API_TITLE: str = "PyQuantAlpha API"
    API_VERSION: str = "0.1.0"
    API_DESCRIPTION: str = "AI 量化策略平台 API - 支持策略生成与回测"
    
    # Binance 配置
    BINANCE_TIMEOUT: int = 10
    BINANCE_MAX_RETRIES: int = 3
    BINANCE_RETRY_DELAY: float = 1.0
    
    # 日志配置
    LOG_LEVEL: str = "INFO"
    LOG_JSON_FORMAT: bool = False
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )

settings = Settings()
