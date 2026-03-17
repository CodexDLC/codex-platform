"""Tests for codex_platform.redis_service.operations.set_ — SetOperations."""

import pytest

from codex_platform.redis_service.operations import SetOperations

pytestmark = pytest.mark.unit


@pytest.fixture
def ops(redis_client):
    return SetOperations(redis_client)


class TestAddMembers:
    async def test_add_and_members(self, ops):
        await ops.add("s1", "a", "b", "c")
        assert await ops.members("s1") == {"a", "b", "c"}

    async def test_add_returns_count(self, ops):
        assert await ops.add("s1", "a", "b") == 2
        assert await ops.add("s1", "b", "c") == 1  # only "c" is new


class TestRemove:
    async def test_remove(self, ops):
        await ops.add("s1", "a", "b", "c")
        removed = await ops.remove("s1", "b")
        assert removed == 1
        assert await ops.members("s1") == {"a", "c"}


class TestIsMember:
    async def test_is_member(self, ops):
        await ops.add("s1", "a")
        assert await ops.is_member("s1", "a") is True
        assert await ops.is_member("s1", "z") is False


class TestCard:
    async def test_card(self, ops):
        await ops.add("s1", "a", "b", "c")
        assert await ops.card("s1") == 3


class TestPop:
    async def test_pop(self, ops):
        await ops.add("s1", "a", "b", "c")
        popped = await ops.pop("s1")
        assert len(popped) == 1
        assert popped.issubset({"a", "b", "c"})
        assert await ops.card("s1") == 2


class TestRandom:
    async def test_random(self, ops):
        await ops.add("s1", "a", "b", "c")
        result = await ops.random("s1", 2)
        assert len(result) == 2
        assert set(result).issubset({"a", "b", "c"})
        # random does not remove
        assert await ops.card("s1") == 3


class TestUnion:
    async def test_union(self, ops):
        await ops.add("s1", "a", "b")
        await ops.add("s2", "b", "c")
        assert await ops.union("s1", "s2") == {"a", "b", "c"}


class TestInter:
    async def test_inter(self, ops):
        await ops.add("s1", "a", "b")
        await ops.add("s2", "b", "c")
        assert await ops.inter("s1", "s2") == {"b"}


class TestDiff:
    async def test_diff(self, ops):
        await ops.add("s1", "a", "b")
        await ops.add("s2", "b", "c")
        assert await ops.diff("s1", "s2") == {"a"}
