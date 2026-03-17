"""Tests for codex_platform.redis_service.operations.hash — HashOperations."""

import pytest

from codex_platform.redis_service.exceptions import RedisDataError
from codex_platform.redis_service.keys import UserKey
from codex_platform.redis_service.operations import HashOperations

pytestmark = pytest.mark.unit


@pytest.fixture
def ops(redis_client):
    return HashOperations(redis_client)


class TestSetGetJson:
    async def test_round_trip(self, ops):
        data = {"name": "Alice", "age": 30}
        await ops.set_json("h:1", "profile", data)
        result = await ops.get_json("h:1", "profile")
        assert result == data

    async def test_get_missing_returns_none(self, ops):
        assert await ops.get_json("h:missing", "f") is None

    async def test_set_non_serializable_raises(self, ops):
        with pytest.raises(RedisDataError, match="serialization"):
            await ops.set_json("h:1", "f", {"bad": object()})

    async def test_get_invalid_json_raises(self, ops, redis_client):
        await redis_client.hset("h:1", "f", "not-json{")
        with pytest.raises(RedisDataError, match="Invalid JSON"):
            await ops.get_json("h:1", "f")


class TestSetGetField:
    async def test_set_get(self, ops):
        await ops.set_field("h:1", "name", "Bob")
        assert await ops.get_field("h:1", "name") == "Bob"

    async def test_get_missing_returns_none(self, ops):
        assert await ops.get_field("h:missing", "x") is None


class TestSetGetFields:
    async def test_set_get_fields(self, ops):
        await ops.set_fields("h:1", {"a": "1", "b": "2"})
        result = await ops.get_fields("h:1", "a", "b", "c")
        assert result == ["1", "2", None]


class TestGetAll:
    async def test_existing(self, ops):
        await ops.set_fields("h:1", {"x": "1", "y": "2"})
        assert await ops.get_all("h:1") == {"x": "1", "y": "2"}

    async def test_missing_returns_none(self, ops):
        assert await ops.get_all("h:missing") is None


class TestDelete:
    async def test_delete_field(self, ops):
        await ops.set_field("h:1", "a", "1")
        removed = await ops.delete_field("h:1", "a")
        assert removed == 1
        assert await ops.get_field("h:1", "a") is None

    async def test_delete_hash(self, ops):
        await ops.set_field("h:1", "a", "1")
        await ops.delete("h:1")
        assert await ops.get_all("h:1") is None


class TestExistsField:
    async def test_exists(self, ops):
        await ops.set_field("h:1", "a", "1")
        assert await ops.exists_field("h:1", "a") is True
        assert await ops.exists_field("h:1", "z") is False


class TestKeysValues:
    async def test_keys_values(self, ops):
        await ops.set_fields("h:1", {"a": "1", "b": "2"})
        assert sorted(await ops.keys("h:1")) == ["a", "b"]
        assert sorted(await ops.values("h:1")) == ["1", "2"]


class TestLength:
    async def test_length(self, ops):
        await ops.set_fields("h:1", {"a": "1", "b": "2"})
        assert await ops.length("h:1") == 2


class TestIncrement:
    async def test_increment(self, ops):
        result = await ops.increment("h:1", "counter", 5)
        assert result == 5
        result = await ops.increment("h:1", "counter")
        assert result == 6


class TestWithBaseRedisKey:
    async def test_set_get_with_user_key(self, ops):
        key = UserKey()
        await ops.set_field(key, "name", "Alice", user_id=42)
        assert await ops.get_field(key, "name", user_id=42) == "Alice"
