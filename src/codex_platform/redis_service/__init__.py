"""
codex_platform.redis_service
==========================
Async Redis service with mixin architecture.

Requires ``redis.asyncio.Redis`` client. All methods are async-only.

Quick start::

    from codex_platform.redis_service import RedisService

    service = RedisService(client=redis_client)
    await service.set_hash_json("my_key", "field", {"a": 1})

Custom composition::

    from codex_platform.redis_service import BaseRedisService, HashMixin, StreamMixin

    class MyRedisService(BaseRedisService, HashMixin, StreamMixin):
        pass

Key Registry::

    from codex_platform.redis_service import UserKey

    await service.get_hash_json(UserKey(), "profile", user_id=42)
"""

from .base import BaseRedisService
from .keys import BaseRedisKey, SessionKey, UserKey
from .managers import BaseRedisManager, SiteSettingsManager
from .operations import (
    HashOperations,
    JsonModuleOperations,
    JsonStringOperations,
    ListOperations,
    PipelineOperations,
    SetOperations,
    StringOperations,
    ZSetOperations,
)
from .service import RedisService

__all__ = [
    "BaseRedisService",
    "RedisService",
    # Managers
    "BaseRedisManager",
    "SiteSettingsManager",
    # Operations
    "HashOperations",
    "SetOperations",
    "ListOperations",
    "StringOperations",
    "ZSetOperations",
    "JsonStringOperations",
    "JsonModuleOperations",
    "PipelineOperations",
    # Key Registry
    "BaseRedisKey",
    "UserKey",
    "SessionKey",
]
