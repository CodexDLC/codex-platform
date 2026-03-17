"""Tests for codex_platform.redis_service.operations.zset — ZSetOperations."""

import pytest

from codex_platform.redis_service.operations import ZSetOperations

pytestmark = pytest.mark.unit


@pytest.fixture
def ops(redis_client):
    return ZSetOperations(redis_client)


class TestAddScore:
    async def test_add_and_score(self, ops):
        added = await ops.add("z1", {"alice": 10.0, "bob": 20.0})
        assert added == 2
        assert await ops.score("z1", "alice") == 10.0
        assert await ops.score("z1", "bob") == 20.0

    async def test_score_missing_returns_none(self, ops):
        assert await ops.score("z1", "nobody") is None


class TestRank:
    async def test_rank(self, ops):
        await ops.add("z1", {"a": 1.0, "b": 2.0, "c": 3.0})
        assert await ops.rank("z1", "a") == 0
        assert await ops.rank("z1", "c") == 2

    async def test_rank_reverse(self, ops):
        await ops.add("z1", {"a": 1.0, "b": 2.0, "c": 3.0})
        assert await ops.rank("z1", "c", reverse=True) == 0
        assert await ops.rank("z1", "a", reverse=True) == 2

    async def test_rank_missing_returns_none(self, ops):
        assert await ops.rank("z1", "nobody") is None


class TestRange:
    async def test_range(self, ops):
        await ops.add("z1", {"a": 1.0, "b": 2.0, "c": 3.0})
        assert await ops.range("z1") == ["a", "b", "c"]

    async def test_range_reverse(self, ops):
        await ops.add("z1", {"a": 1.0, "b": 2.0, "c": 3.0})
        assert await ops.range("z1", reverse=True) == ["c", "b", "a"]

    async def test_range_with_scores(self, ops):
        await ops.add("z1", {"a": 1.0, "b": 2.0})
        result = await ops.range("z1", with_scores=True)
        assert result == [("a", 1.0), ("b", 2.0)]


class TestRangeByScore:
    async def test_range_by_score(self, ops):
        await ops.add("z1", {"a": 1.0, "b": 5.0, "c": 10.0})
        result = await ops.range_by_score("z1", 2.0, 10.0)
        assert result == ["b", "c"]


class TestRemove:
    async def test_remove(self, ops):
        await ops.add("z1", {"a": 1.0, "b": 2.0})
        removed = await ops.remove("z1", "a")
        assert removed == 1
        assert await ops.score("z1", "a") is None


class TestCard:
    async def test_card(self, ops):
        await ops.add("z1", {"a": 1.0, "b": 2.0, "c": 3.0})
        assert await ops.card("z1") == 3


class TestIncrement:
    async def test_increment(self, ops):
        await ops.add("z1", {"a": 10.0})
        new_score = await ops.increment("z1", "a", 5.0)
        assert new_score == 15.0


class TestCount:
    async def test_count(self, ops):
        await ops.add("z1", {"a": 1.0, "b": 5.0, "c": 10.0})
        assert await ops.count("z1", 1.0, 5.0) == 2


class TestRemoveByRank:
    async def test_remove_by_rank(self, ops):
        await ops.add("z1", {"a": 1.0, "b": 2.0, "c": 3.0})
        removed = await ops.remove_by_rank("z1", 0, 0)
        assert removed == 1
        assert await ops.score("z1", "a") is None


class TestRemoveByScore:
    async def test_remove_by_score(self, ops):
        await ops.add("z1", {"a": 1.0, "b": 5.0, "c": 10.0})
        removed = await ops.remove_by_score("z1", 1.0, 5.0)
        assert removed == 2
        assert await ops.card("z1") == 1
