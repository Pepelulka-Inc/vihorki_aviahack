"""
Configuration for Metrics Analyzer Service
"""

import os
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


class MetricsAnalyzerConfig(BaseSettings):
    """Configuration for the metrics analyzer service"""
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensetive="false",
        extra="ignore"
    )
    
    metrics_api_url: str = Field(
        default="http://localhost:8080",
        description="Base URL for metrics API endpoint"
    )
    metrics_api_key: Optional[str] = Field(
        default=None,
        description="API key for metrics endpoint authentication"
    )
    
    yandex_folder_id: Optional[str] = Field(
        default=None,
        validation_alias="YANDEX_FOLDER_ID",
        description="Yandex Cloud folder ID"
    )
    yandex_api_key: Optional[str] = Field(
        default=None,
        validation_alias="YANDEX_API_KEY",
        description="Yandex Cloud API key"
    )
    yandex_llm_model: str = Field(
        default="qwen3-235b-a22b-fp8",
        description="LLM model to use for analysis"
    )
    yandex_base_url: str = Field(
        default="https://rest-assistant.api.cloud.yandex.net/v1",
        description="Yandex Cloud API base URL"
    )
    
    log_level: str = Field(
        default="INFO",
        description="Logging level"
    )
    request_timeout: float = Field(
        default=30.0,
        description="HTTP request timeout in seconds"
    )
    
    default_reasoning_effort: str = Field(
        default="medium",
        description="Default LLM reasoning effort (low, medium, high)"
    )
    enable_api_submission: bool = Field(
        default=True,
        description="Enable submission to metrics API"
    )
    enable_llm_analysis: bool = Field(
        default=True,
        description="Enable LLM analysis"
    )


def load_config() -> MetricsAnalyzerConfig:
    """Load configuration from environment variables and .env file"""
    return MetricsAnalyzerConfig()