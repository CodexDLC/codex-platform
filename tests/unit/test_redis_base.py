"""Tests for codex_platform.redis_service.base — catch_redis_errors decorator."""

import pytest
from redis.exceptions import ConnectionError, RedisError, TimeoutError

from codex_platform.redis_service.base import catch_redis_errors
from codex_platform.redis_service.exceptions import RedisConnectionError, RedisServiceError

pytestmark = pytest.mark.unit


class TestCatchRedisErrors:
    async def test_normal_execution(self):
        @catch_redis_errors
        async def ok():
            return "result"

        assert await ok() == "result"

    async def test_connection_error(self):
        @catch_redis_errors
        async def fail():
            raise ConnectionError("gone")

        with pytest.raises(RedisConnectionError, match="Network failure"):
            await fail()

    async def test_timeout_error(self):
        @catch_redis_errors
        async def fail():
            raise TimeoutError("slow")

        with pytest.raises(RedisConnectionError, match="Network failure"):
            await fail()

    async def test_redis_error(self):
        @catch_redis_errors
        async def fail():
            raise RedisError("oops")

        with pytest.raises(RedisServiceError, match="Operation failed"):
            await fail()

    async def test_preserves_cause(self):
        @catch_redis_errors
        async def fail():
            raise ConnectionError("root cause")

        with pytest.raises(RedisConnectionError) as exc_info:
            await fail()
        assert isinstance(exc_info.value.__cause__, ConnectionError)
