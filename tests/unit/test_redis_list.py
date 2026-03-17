"""Tests for codex_platform.redis_service.operations.list_ — ListOperations."""

import pytest

from codex_platform.redis_service.operations import ListOperations

pytestmark = pytest.mark.unit


@pytest.fixture
def ops(redis_client):
    return ListOperations(redis_client)


class TestPushPop:
    async def test_push_and_pop(self, ops):
        await ops.push("lst", "a", "b", "c")
        assert await ops.pop("lst") == "a"
        assert await ops.pop("lst") == "b"

    async def test_pop_empty_returns_none(self, ops):
        assert await ops.pop("empty") is None


class TestLpush:
    async def test_lpush(self, ops):
        await ops.lpush("lst", "a", "b")
        items = await ops.range("lst")
        assert items == ["b", "a"]


class TestRpop:
    async def test_rpop(self, ops):
        await ops.push("lst", "a", "b", "c")
        assert await ops.rpop("lst") == "c"

    async def test_rpop_empty_returns_none(self, ops):
        assert await ops.rpop("empty") is None


class TestRange:
    async def test_range_full(self, ops):
        await ops.push("lst", "a", "b", "c")
        assert await ops.range("lst") == ["a", "b", "c"]

    async def test_range_slice(self, ops):
        await ops.push("lst", "a", "b", "c", "d")
        assert await ops.range("lst", 1, 2) == ["b", "c"]


class TestLength:
    async def test_length(self, ops):
        assert await ops.length("lst") == 0
        await ops.push("lst", "a", "b")
        assert await ops.length("lst") == 2


class TestSetIndex:
    async def test_set_index(self, ops):
        await ops.push("lst", "a", "b", "c")
        await ops.set_index("lst", 1, "X")
        assert await ops.range("lst") == ["a", "X", "c"]


class TestTrim:
    async def test_trim(self, ops):
        await ops.push("lst", "a", "b", "c", "d")
        await ops.trim("lst", 1, 2)
        assert await ops.range("lst") == ["b", "c"]


class TestMove:
    async def test_move(self, ops):
        await ops.push("src", "a", "b", "c")
        moved = await ops.move("src", "dst")
        assert moved == "c"
        assert await ops.range("src") == ["a", "b"]
        assert await ops.range("dst") == ["c"]

    async def test_move_empty_returns_none(self, ops):
        assert await ops.move("empty", "dst") is None
