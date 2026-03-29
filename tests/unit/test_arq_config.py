"""Tests for codex_platform.workers.arq.config."""

from __future__ import annotations

import pytest

from codex_platform.workers.arq.config import BaseWorkerConfig

pytestmark = pytest.mark.unit


class TestBaseWorkerConfig:
    def test_reads_django_style_email_aliases(self):
        config = BaseWorkerConfig(
            EMAIL_HOST="smtp.example.com",
            EMAIL_PORT=587,
            EMAIL_HOST_USER="bot",
            EMAIL_HOST_PASSWORD="secret",  # pragma: allowlist secret
            DEFAULT_FROM_EMAIL="noreply@example.com",
            EMAIL_USE_TLS=True,
            EMAIL_USE_SSL=False,
        )

        assert config.SMTP_HOST == "smtp.example.com"
        assert config.SMTP_PORT == 587
        assert config.SMTP_USER == "bot"
        assert config.SMTP_PASSWORD == "secret"  # pragma: allowlist secret
        assert config.SMTP_FROM_EMAIL == "noreply@example.com"
        assert config.SMTP_USE_TLS is True
        assert config.SMTP_USE_SSL is False

    def test_inherits_redis_fields_from_base_common_settings(self):
        config = BaseWorkerConfig(
            redis_host="redis.internal",
            redis_port=6380,
            redis_password="pw",  # pragma: allowlist secret
        )

        assert config.redis_host == "redis.internal"
        assert config.redis_port == 6380
        assert config.redis_password == "pw"  # pragma: allowlist secret
        assert config.redis_url == "redis://:pw@redis.internal:6380"

    def test_builds_arq_redis_settings_from_base_redis_fields(self):
        config = BaseWorkerConfig(
            redis_host="redis.internal",
            redis_port=6380,
            redis_password="pw",  # pragma: allowlist secret
        )

        redis_settings = config.arq_redis_settings

        assert redis_settings.host == "redis.internal"
        assert redis_settings.port == 6380
        assert redis_settings.password == "pw"  # pragma: allowlist secret
