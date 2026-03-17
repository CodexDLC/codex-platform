"""
codex_platform.redis_service.service
===================================
Full Redis service combining all mixins.

Use RedisService if you need all operations.
For selective composition, combine mixins manually::

    from codex_platform.redis_service import BaseRedisService, HashMixin, StreamMixin

    class MyRedisService(BaseRedisService, HashMixin, StreamMixin):
        pass
"""

from .base import BaseRedisService
from .mixins import HashMixin, JsonMixin, ListMixin, PipelineMixin, SetMixin, StreamMixin, StringMixin


class RedisService(
    BaseRedisService,
    PipelineMixin,
    HashMixin,
    SetMixin,
    ListMixin,
    StringMixin,
    StreamMixin,
    JsonMixin,
):
    """Full Redis service with all operations. Use it or compose your own via mixins."""
