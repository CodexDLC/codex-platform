"""
codex_platform.redis_service.managers
=======================================
Business-logic managers built on top of Operations.

Create project-specific managers here::

    from codex_platform.redis_service.managers import BaseRedisManager
    from codex_platform.redis_service.operations import HashOperations

    class SiteSettingsManager(BaseRedisManager):
        async def get_settings(self) -> dict:
            return await self.hash.get_all("site:settings") or {}
"""

from .base_manager import BaseRedisManager

__all__ = ["BaseRedisManager"]
