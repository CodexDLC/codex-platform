"""Tests for codex_platform.redis_service.operations.string — StringOperations."""

import pytest

from codex_platform.redis_service.operations import StringOperations

pytestmark = pytest.mark.unit


@pytest.fixture
def ops(redis_client):
    return StringOperations(redis_client)


class TestSetGet:
    async def test_round_trip(self, ops):
        await ops.set("k1", "v1")
        assert await ops.get("k1") == "v1"

    async def test_set_with_ttl(self, ops, redis_client):
        await ops.set("k1", "v1", ttl=300)
        remaining = await redis_client.ttl("k1")
        assert 0 < remaining <= 300

    async def test_get_missing_returns_none(self, ops):
        assert await ops.get("missing") is None


class TestSetnx:
    async def test_first_returns_true(self, ops):
        assert await ops.setnx("k1", "v1") is True

    async def test_second_returns_false(self, ops):
        await ops.set("k1", "v1")
        assert await ops.setnx("k1", "v2") is False
        assert await ops.get("k1") == "v1"


class TestGetset:
    async def test_returns_old_value(self, ops):
        await ops.set("k1", "old")
        old = await ops.getset("k1", "new")
        assert old == "old"
        assert await ops.get("k1") == "new"

    async def test_returns_none_if_missing(self, ops):
        assert await ops.getset("k1", "val") is None


class TestMgetMset:
    async def test_mset_mget(self, ops):
        await ops.mset({"a": "1", "b": "2"})
        result = await ops.mget("a", "b", "c")
        assert result == ["1", "2", None]


class TestIncrIncrby:
    async def test_incr(self, ops):
        assert await ops.incr("counter") == 1
        assert await ops.incr("counter") == 2

    async def test_incrby(self, ops):
        assert await ops.incrby("counter", 10) == 10
        assert await ops.incrby("counter", 5) == 15


class TestAppend:
    async def test_append(self, ops):
        await ops.set("k1", "hello")
        length = await ops.append("k1", " world")
        assert length == 11
        assert await ops.get("k1") == "hello world"


class TestDelete:
    async def test_delete(self, ops):
        await ops.set("k1", "v1")
        await ops.delete("k1")
        assert await ops.get("k1") is None


class TestDeleteByPattern:
    async def test_delete_by_pattern(self, ops):
        await ops.mset({"pfx:a": "1", "pfx:b": "2", "other": "3"})
        deleted = await ops.delete_by_pattern("pfx:*")
        assert deleted == 2
        assert await ops.get("other") == "3"

    async def test_no_match_returns_zero(self, ops):
        assert await ops.delete_by_pattern("no_match:*") == 0


class TestExpireTtl:
    async def test_expire_and_ttl(self, ops):
        await ops.set("k1", "v1")
        assert await ops.expire("k1", 60) is True
        remaining = await ops.ttl("k1")
        assert 0 < remaining <= 60

    async def test_ttl_no_key(self, ops):
        assert await ops.ttl("missing") == -2

    async def test_ttl_no_expire(self, ops):
        await ops.set("k1", "v1")
        assert await ops.ttl("k1") == -1


class TestExists:
    async def test_exists(self, ops):
        assert await ops.exists("k1") is False
        await ops.set("k1", "v1")
        assert await ops.exists("k1") is True


class TestRename:
    async def test_rename(self, ops):
        await ops.set("old", "val")
        await ops.rename("old", "new")
        assert await ops.get("old") is None
        assert await ops.get("new") == "val"


class TestKeyType:
    async def test_string_type(self, ops):
        await ops.set("k1", "v1")
        assert await ops.key_type("k1") == "string"
