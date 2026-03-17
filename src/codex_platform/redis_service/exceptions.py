"""
codex_platform.redis_service.exceptions
=======================================
Кастомные исключения для работы с Redis.

Используй эти классы в бизнес-логике вместо redis.exceptions.*
чтобы не зависеть от внутренностей redis-py.
"""


class RedisServiceError(Exception):
    """Базовый класс для всех ошибок слоя Redis."""


class RedisConnectionError(RedisServiceError):
    """Ошибки сети: таймауты, недоступность сервера, обрывы связи."""


class RedisDataError(RedisServiceError):
    """Ошибки контента: битый JSON, несовпадение типов."""
