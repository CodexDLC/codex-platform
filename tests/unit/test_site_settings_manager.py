"""Tests for codex_platform.redis_service.managers.site_settings — SiteSettingsManager."""

import pytest

from codex_platform.redis_service.managers.site_settings import SiteSettingsManager

pytestmark = pytest.mark.unit


@pytest.fixture
def manager(redis_client):
    return SiteSettingsManager(redis_client)


class TestSiteSettingsManager:
    async def test_get_all_empty(self, manager):
        result = await manager.aget_all()
        assert result == {}

    async def test_exists_false_when_empty(self, manager):
        assert await manager.aexists() is False

    async def test_set_and_get_field(self, manager):
        await manager.aset_field("maintenance", "false")
        assert await manager.aget_field("maintenance") == "false"

    async def test_get_field_missing(self, manager):
        assert await manager.aget_field("nonexistent") is None

    async def test_set_fields_and_get_all(self, manager):
        data = {"maintenance": "false", "version": "1.2", "debug": "true"}
        await manager.aset_fields(data)
        result = await manager.aget_all()
        assert result == data

    async def test_exists_true_after_set(self, manager):
        await manager.aset_field("key", "value")
        assert await manager.aexists() is True

    async def test_set_field_overwrites(self, manager):
        await manager.aset_field("mode", "on")
        await manager.aset_field("mode", "off")
        assert await manager.aget_field("mode") == "off"

    async def test_cache_key_constant(self, manager):
        assert manager.CACHE_KEY == "site_settings"
