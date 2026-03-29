"""
codex_platform.redis_service.managers.site_settings
=====================================================
Manager for accessing site-wide settings stored in a Redis hash.
"""

from __future__ import annotations

from typing import cast

from codex_platform.redis_service.managers.base_manager import BaseRedisManager


class SiteSettingsManager(BaseRedisManager):
    """Async interface to the shared ``site_settings`` Redis hash.

    Provides a fixed CACHE_KEY so that all services in the Codex ecosystem
    read and write the same Redis key without coupling to Django models.

    Example::

        manager = SiteSettingsManager(redis_client)
        await manager.aset_fields({"maintenance": "false", "version": "1.2"})
        value = await manager.aget_field("maintenance")
        all_settings = await manager.aget_all()
    """

    CACHE_KEY = "site_settings"

    async def aget_all(self) -> dict[str, str]:
        """Return all settings as a flat dict (HGETALL).

        Returns:
            Dict of ``{field: value}``. Empty dict if no settings are cached.
        """
        result = await self.hash.get_all(self.CACHE_KEY)
        return result or {}

    async def aget_field(self, field: str) -> str | None:
        """Return a single setting value (HGET).

        Args:
            field: Setting name.

        Returns:
            String value, or ``None`` if the field does not exist.
        """
        return cast("str | None", await self.hash.get_field(self.CACHE_KEY, field))

    async def aset_field(self, field: str, value: str) -> None:
        """Write a single setting atomically (HSET).

        Args:
            field: Setting name.
            value: String value to store.
        """
        await self.hash.set_field(self.CACHE_KEY, field, value)

    async def aset_fields(self, data: dict[str, str]) -> None:
        """Write multiple settings in a single call (HSET mapping).

        Args:
            data: Mapping of ``{field: value}`` pairs.
        """
        await self.hash.set_fields(self.CACHE_KEY, data)

    async def aexists(self) -> bool:
        """Check whether any settings are present in the cache (HLEN > 0).

        Returns:
            ``True`` if the hash key exists and has at least one field.
        """
        return cast(int, await self.hash.length(self.CACHE_KEY)) > 0
