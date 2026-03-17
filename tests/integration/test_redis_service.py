"""
Integration tests for RedisService with a real Redis instance.

Uses REDIS_URL env var (set by CI). Locally requires Redis running on localhost:6379.
Each test gets a clean DB via the `clean_redis` fixture (flushdb after test).

Covers:
- HashOperations: set_json / get_json / get_all
- StringOperations: set with TTL / get / ttl
- PipelineOperations: batch execute / atomic transact
"""

import pytest
from redis.asyncio import Redis

from codex_platform.redis_service.operations import HashOperations, StringOperations
from codex_platform.redis_service.operations.pipeline import PipelineOperations
from codex_platform.redis_service.service import RedisService

# ---------------------------------------------------------------------------
# RedisService composition
# ---------------------------------------------------------------------------


@pytest.mark.integration
async def test_redis_service_composes_all_operations(clean_redis: Redis) -> None:
    """RedisService exposes all operation namespaces on the same client."""
    service = RedisService(clean_redis)
    assert isinstance(service.hash, HashOperations)
    assert isinstance(service.string, StringOperations)
    assert isinstance(service.pipeline, PipelineOperations)


# ---------------------------------------------------------------------------
# HashOperations
# ---------------------------------------------------------------------------


@pytest.mark.integration
async def test_hash_set_json_and_get_json(clean_redis: Redis) -> None:
    """set_json stores a dict; get_json returns it unchanged."""
    ops = HashOperations(clean_redis)
    payload = {"user_id": 42, "name": "Alex", "active": True}

    await ops.set_json("integration:hash:user", "profile", payload)
    result = await ops.get_json("integration:hash:user", "profile")

    assert result == payload


@pytest.mark.integration
async def test_hash_get_all_returns_all_fields(clean_redis: Redis) -> None:
    """set_fields stores multiple fields; get_all returns them all."""
    ops = HashOperations(clean_redis)
    data = {"field_a": "value_a", "field_b": "value_b"}

    await ops.set_fields("integration:hash:multi", data)
    result = await ops.get_all("integration:hash:multi")

    assert result == data


@pytest.mark.integration
async def test_hash_missing_key_returns_none(clean_redis: Redis) -> None:
    """get_json on a non-existent key returns None without raising."""
    ops = HashOperations(clean_redis)
    result = await ops.get_json("integration:hash:nonexistent", "field")
    assert result is None


# ---------------------------------------------------------------------------
# StringOperations
# ---------------------------------------------------------------------------


@pytest.mark.integration
async def test_string_set_and_get(clean_redis: Redis) -> None:
    """set stores a value; get retrieves it."""
    ops = StringOperations(clean_redis)

    await ops.set("integration:string:key", "hello_codex")
    result = await ops.get("integration:string:key")

    assert result == "hello_codex"


@pytest.mark.integration
async def test_string_set_with_ttl(clean_redis: Redis) -> None:
    """set with ttl=60 results in a positive TTL on the key."""
    ops = StringOperations(clean_redis)

    await ops.set("integration:string:ttl_key", "ephemeral", ttl=60)
    remaining_ttl = await ops.ttl("integration:string:ttl_key")

    assert 0 < remaining_ttl <= 60


@pytest.mark.integration
async def test_string_missing_key_returns_none(clean_redis: Redis) -> None:
    """get on a non-existent key returns None without raising."""
    ops = StringOperations(clean_redis)
    result = await ops.get("integration:string:nonexistent")
    assert result is None


# ---------------------------------------------------------------------------
# PipelineOperations
# ---------------------------------------------------------------------------


@pytest.mark.integration
async def test_pipeline_batch_execute(clean_redis: Redis) -> None:
    """execute() sends multiple SETs in one batch; all values are readable after."""
    ops = PipelineOperations(clean_redis)
    str_ops = StringOperations(clean_redis)

    async def build(pipe):  # type: ignore[no-untyped-def]
        await pipe.set("integration:pipe:k1", "v1")
        await pipe.set("integration:pipe:k2", "v2")
        await pipe.set("integration:pipe:k3", "v3")

    await ops.execute(build)

    assert await str_ops.get("integration:pipe:k1") == "v1"
    assert await str_ops.get("integration:pipe:k2") == "v2"
    assert await str_ops.get("integration:pipe:k3") == "v3"


@pytest.mark.integration
async def test_pipeline_atomic_transact(clean_redis: Redis) -> None:
    """transact() wraps commands in MULTI/EXEC; all succeed atomically."""
    ops = PipelineOperations(clean_redis)
    str_ops = StringOperations(clean_redis)

    await str_ops.set("integration:pipe:counter", "10")

    async def transfer(pipe):  # type: ignore[no-untyped-def]
        await pipe.decrby("integration:pipe:counter", 3)
        await pipe.incrby("integration:pipe:counter", 1)

    await ops.transact(transfer)

    result = await str_ops.get("integration:pipe:counter")
    assert result == "8"  # 10 - 3 + 1
