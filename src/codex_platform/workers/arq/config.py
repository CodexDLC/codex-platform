"""
codex_platform.workers.arq.config
================================
Base workers configuration with SMTP and ARQ fields.

Extends BaseCommonSettings from codex_core.settings.
Maps standard Django .env names to workers-friendly fields.

Usage:
    class MyWorkerConfig(BaseWorkerConfig):
        SEVEN_IO_API_KEY: str | None = None  # project-specific
        TEMPLATES_DIR: str = "src/workers/templates"

        class Config:
            env_file = ".env"
"""

from typing import Any

from codex_core.settings import BaseCommonSettings
from pydantic import Field


class BaseWorkerConfig(BaseCommonSettings):
    """Base configuration for ARQ workers — provides SMTP and ARQ settings.

    Maps standard Django ``.env`` variable names (``EMAIL_HOST``, etc.) to
    internal ``SMTP_``-prefixed fields for clarity.

    Extend this class in your project to add vendor-specific fields
    (Twilio, Seven.io, SendGrid, etc.).

    Example::

        class MyWorkerConfig(BaseWorkerConfig):
            SEVEN_IO_API_KEY: str | None = None
            TEMPLATES_DIR: str = "src/workers/templates"

            class Config:
                env_file = ".env"
    """

    # --- Email (SMTP) — маппинг Django env names ---
    SMTP_HOST: str = Field(default="localhost", alias="EMAIL_HOST")
    SMTP_PORT: int = Field(default=465, alias="EMAIL_PORT")
    SMTP_USER: str | None = Field(default=None, alias="EMAIL_HOST_USER")
    SMTP_PASSWORD: str | None = Field(default=None, alias="EMAIL_HOST_PASSWORD")
    SMTP_FROM_EMAIL: str | None = Field(default=None, alias="DEFAULT_FROM_EMAIL")
    SMTP_USE_TLS: bool = Field(default=False, alias="EMAIL_USE_TLS")
    SMTP_USE_SSL: bool = Field(default=True, alias="EMAIL_USE_SSL")

    # --- ARQ Configuration ---
    arq_max_jobs: int = 10
    arq_job_timeout: int = 60
    arq_keep_result: int = 60

    @property
    def arq_redis_settings(self) -> Any:
        """Build and return an ARQ ``RedisSettings`` object from the base Redis config."""
        from arq.connections import RedisSettings

        return RedisSettings(
            host=self.redis_host,
            port=self.redis_port,
            password=self.redis_password,
        )
