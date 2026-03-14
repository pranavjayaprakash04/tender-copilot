from __future__ import annotations

from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env', env_file_encoding='utf-8')
    # App
    SECRET_KEY: str = Field(..., description="JWT secret key")
    ENVIRONMENT: Literal["development", "production", "test"] = "development"
    LOG_LEVEL: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"

    # Database
    DATABASE_URL: str = Field(..., description="PostgreSQL connection URL")

    # Supabase
    SUPABASE_URL: str = Field(..., description="Supabase project URL")
    SUPABASE_ANON_KEY: str = Field(..., description="Supabase anonymous key")
    SUPABASE_SERVICE_ROLE_KEY: str = Field(..., description="Supabase service role key")
    SUPABASE_JWT_SECRET: str = Field(default="", description="Supabase JWT secret")

    # Groq
    GROQ_API_KEY: str = Field(..., description="Groq API key")

    # Redis
    REDIS_URL: str = Field(..., description="Redis connection URL")

    # WhatsApp
    WHATSAPP_ACCESS_TOKEN: str = Field(..., description="WhatsApp Cloud API access token")
    WHATSAPP_PHONE_NUMBER_ID: str = Field(..., description="WhatsApp phone number ID")
    WHATSAPP_APP_SECRET: str = Field(..., description="WhatsApp app secret for webhook verification")

    # Resend
    RESEND_API_KEY: str = Field(..., description="Resend API key for email")

    # Razorpay
    RAZORPAY_KEY_ID: str = Field(..., description="Razorpay key ID")
    RAZORPAY_KEY_SECRET: str = Field(..., description="Razorpay key secret")

    # Celery
    CELERY_BROKER_URL: str = Field(default="", description="Celery broker URL (defaults to REDIS_URL)")
    CELERY_RESULT_BACKEND: str = Field(default="", description="Celery result backend (defaults to REDIS_URL)")

    @field_validator("CELERY_BROKER_URL", mode='before')
    @classmethod
    def set_celery_broker(cls, v, info):
        return v or info.data.get("REDIS_URL", "")

    @field_validator("CELERY_RESULT_BACKEND", mode='before')
    @classmethod
    def set_celery_backend(cls, v, info):
        return v or info.data.get("REDIS_URL", "")

    # CORS
    CORS_ORIGINS: list[str] = Field(
        default=["http://localhost:3000", "http://localhost:3001", "https://nivedha.ai", "https://www.nivedha.ai"],
        description="Allowed CORS origins"
    )

    # File uploads
    MAX_FILE_SIZE: int = Field(default=10 * 1024 * 1024, description="Max file size in bytes (10MB)")

    # AI Model Settings
    GROQ_DEFAULT_MODEL: str = "llama-3.3-70b-versatile"
    GROQ_FAST_MODEL: str = "llama-3.1-8b-instant"
    GROQ_REASONING_MODEL: str = "deepseek-r1-distill-llama-70b"

    # Rate limiting
    RATE_LIMIT_REQUESTS: int = Field(default=100, description="Requests per minute")
    RATE_LIMIT_WINDOW: int = Field(default=60, description="Rate limit window in seconds")


settings = Settings()
