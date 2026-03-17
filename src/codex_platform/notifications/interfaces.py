"""
codex_platform.core.interfaces
============================
Protocol contracts for core adapters.
The library core relies only on these interfaces, not on concrete ORM models.
"""

from __future__ import annotations

from typing import Protocol


class ContentProvider(Protocol):
    """Provides translated template text by key."""

    def get_text(self, key: str) -> str | None:
        """Return translated text or None if not found."""
        ...


class ContentCacheAdapter(Protocol):
    """Adapter for caching email/notification content (used by BaseEmailContentSelector)."""

    def get_cached_value(self, key: str) -> str | None:
        """Return cached string value or None if not found."""
        ...

    def set_cached_value(self, key: str, value: str, timeout: int) -> None:
        """Store value in cache with given timeout (seconds)."""
        ...
