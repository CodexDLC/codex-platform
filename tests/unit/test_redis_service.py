"""Tests for codex_platform.redis_service.service — RedisService composition."""

import pytest

from codex_platform.redis_service.operations import (
    HashOperations,
    JsonModuleOperations,
    JsonStringOperations,
    ListOperations,
    PipelineOperations,
    SetOperations,
    StringOperations,
    ZSetOperations,
)
from codex_platform.redis_service.service import RedisService

pytestmark = pytest.mark.unit


@pytest.fixture
def service(redis_client):
    return RedisService(redis_client)


class TestComposition:
    def test_all_operations_accessible(self, service):
        assert isinstance(service.hash, HashOperations)
        assert isinstance(service.string, StringOperations)
        assert isinstance(service.list, ListOperations)
        assert isinstance(service.set, SetOperations)
        assert isinstance(service.zset, ZSetOperations)
        assert isinstance(service.json_module, JsonModuleOperations)
        assert isinstance(service.json, JsonStringOperations)
        assert isinstance(service.pipeline, PipelineOperations)


class TestIntegration:
    async def test_string_set_get(self, service):
        await service.string.set("k1", "v1")
        assert await service.string.get("k1") == "v1"

    async def test_hash_set_get(self, service):
        await service.hash.set_field("h:1", "name", "Alice")
        assert await service.hash.get_field("h:1", "name") == "Alice"
