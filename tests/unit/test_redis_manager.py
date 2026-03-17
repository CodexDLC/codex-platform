"""Tests for codex_platform.redis_service.managers.base_manager — BaseRedisManager."""

import pytest

from codex_platform.redis_service.managers.base_manager import BaseRedisManager
from codex_platform.redis_service.operations import HashOperations, StringOperations

pytestmark = pytest.mark.unit


@pytest.fixture
def manager(redis_client):
    return BaseRedisManager(redis_client)


class TestBaseRedisManager:
    def test_has_hash_operations(self, manager):
        assert isinstance(manager.hash, HashOperations)

    def test_has_string_operations(self, manager):
        assert isinstance(manager.string, StringOperations)

    async def test_operations_work(self, manager):
        await manager.string.set("mgr:k", "v")
        assert await manager.string.get("mgr:k") == "v"

        await manager.hash.set_field("mgr:h", "f", "val")
        assert await manager.hash.get_field("mgr:h", "f") == "val"
