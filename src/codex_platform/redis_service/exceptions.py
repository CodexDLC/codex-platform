"""
codex_platform.redis_service.exceptions
=======================================
Custom exceptions for the Redis service layer.

Use these classes in business logic instead of redis.exceptions.*
to avoid coupling to redis-py internals.
"""


class RedisServiceError(Exception):
    """Base class for all Redis layer errors."""


class RedisConnectionError(RedisServiceError):
    """Network errors: timeouts, server unavailability, connection drops."""


class RedisDataError(RedisServiceError):
    """Content errors: malformed JSON, type mismatches."""
