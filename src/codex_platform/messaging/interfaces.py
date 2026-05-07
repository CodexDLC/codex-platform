"""Protocol contracts for messaging adapters."""

from __future__ import annotations

from typing import Protocol


class ContentProvider(Protocol):
    """Provides translated template text by key."""

    def get_text(self, key: str) -> str | None:
        """Return translated text or None if not found."""
        ...


class ContentCacheAdapter(Protocol):
    """Adapter for caching email/notification content."""

    def get_cached_value(self, key: str) -> str | None:
        """Return cached string value or None if not found."""
        ...

    def set_cached_value(self, key: str, value: str, timeout: int) -> None:
        """Store value in cache with given timeout in seconds."""
        ...


__all__ = ["ContentProvider", "ContentCacheAdapter"]
