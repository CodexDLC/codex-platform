"""
codex_platform.redis_service.service
=====================================
Full Redis service via composition.

Usage::

    from redis.asyncio import Redis
    from codex_platform.redis_service import RedisService

    redis_client = Redis(host="localhost", port=6379)
    service = RedisService(redis_client)

    await service.hash.set_json("u:42", "profile", data)
    await service.string.set("session:abc", "token", ttl=3600)

    # JSON as plain string (no server modules required):
    await service.json.set("user:42", {"name": "Alice"}, ttl=3600)
    user = await service.json.get("user:42")

    # JSON via RedisJSON module (requires server module):
    await service.json_module.set("user:42", "$", {"name": "Alice"})
    name = await service.json_module.get("user:42", "$.name")

For selective composition use operations directly::

    from codex_platform.redis_service.operations import HashOperations, StringOperations

    class MyService:
        def __init__(self, client: Redis):
            self.hash = HashOperations(client)
            self.string = StringOperations(client)
"""

from redis.asyncio import Redis

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


class RedisService:
    """Unified Redis service — all data-type operations in one place.

    Suitable for projects that need access to multiple Redis data types through
    a single entry point.  For selective composition, instantiate individual
    ``Operations`` classes directly.

    Attributes:
        hash: Hash operations (HSET / HGET / HGETALL …).
        string: String and key-level operations (SET / GET / EXPIRE …).
        list: List operations (RPUSH / LPOP / LRANGE …).
        set: Set operations (SADD / SREM / SMEMBERS …).
        zset: Sorted-set operations (ZADD / ZRANGE / ZRANK …).
        json: JSON stored as Redis strings — works with any Redis instance.
        json_module: JSON via the server-side RedisJSON module (requires RedisJSON).
        pipeline: Pipeline / transaction helpers.
    """

    def __init__(self, client: Redis) -> None:
        """Initialize the service with an existing async Redis client.

        Args:
            client: An already-constructed ``redis.asyncio.Redis`` instance.
        """
        self.hash = HashOperations(client)
        self.string = StringOperations(client)
        self.list = ListOperations(client)
        self.set = SetOperations(client)
        self.zset = ZSetOperations(client)
        self.json = JsonStringOperations(client)
        self.json_module = JsonModuleOperations(client)
        self.pipeline = PipelineOperations(client)
