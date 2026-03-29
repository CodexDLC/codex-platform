"""
codex_platform.redis_service.managers
=======================================
High-level business-logic managers built on top of low-level Operations.

Each manager encapsulates a specific domain area and exposes a clean async
API without requiring callers to know Redis key names or data structures.

Modules
-------
base_manager.py
    ``BaseRedisManager`` — base class that wires up ``HashOperations`` and
    ``StringOperations`` for every subclass. Inherit from it to build your
    own domain managers.

site_settings.py
    ``SiteSettingsManager`` — manages the shared ``"site_settings"`` Redis
    hash. Django writes settings to it; bots and ARQ workers read from it
    without coupling to Django models.

Available imports
-----------------
::

    from codex_platform.redis_service.managers import BaseRedisManager, SiteSettingsManager

    # or via the top-level shortcut:
    from codex_platform.redis_service import SiteSettingsManager

    manager = SiteSettingsManager(redis_client)
    await manager.aset_fields({"maintenance": "false", "version": "2.0"})
    value = await manager.aget_field("maintenance")   # -> "false"
    all_s  = await manager.aget_all()                  # -> {"maintenance": "false", ...}
    exists = await manager.aexists()                   # -> True
"""

from .base_manager import BaseRedisManager
from .site_settings import SiteSettingsManager

__all__ = ["BaseRedisManager", "SiteSettingsManager"]
