import os

import pytest
from redis.asyncio import Redis


@pytest.fixture
async def redis_client():
    """Real Redis client for integration tests. Uses REDIS_URL env var (set by CI)."""
    url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    client = Redis.from_url(url, decode_responses=True)
    yield client
    await client.aclose()


@pytest.fixture
async def clean_redis(redis_client: Redis):
    """Redis client that flushes the test DB after each test."""
    yield redis_client
    await redis_client.flushdb()
