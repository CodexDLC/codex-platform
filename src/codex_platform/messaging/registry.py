"""Delivery channel registry."""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any

from .orchestrator import DeliveryChannel

log = logging.getLogger(__name__)


class ChannelRegistry:
    """Registry for config-driven delivery channel factories."""

    def __init__(self) -> None:
        self._factories: list[tuple[str, Callable[[Any], DeliveryChannel | None]]] = []

    def register(
        self,
        name: str,
        factory: Callable[[Any], DeliveryChannel | None],
    ) -> None:
        """Register a channel factory."""

        if any(existing == name for existing, _factory in self._factories):
            log.warning("ChannelRegistry | duplicate registration for %s", name)
        self._factories.append((name, factory))

    def build_channels(self, config: Any) -> list[DeliveryChannel]:
        """Build available channels from registered factories."""

        channels: list[DeliveryChannel] = []
        for name, factory in self._factories:
            try:
                channel = factory(config)
                if channel is not None and channel.is_available():
                    channels.append(channel)
                    log.info("ChannelRegistry | %s enabled", name)
                else:
                    log.debug("ChannelRegistry | %s skipped (not configured)", name)
            except Exception:
                log.exception("ChannelRegistry | %s factory failed", name)
        return channels


__all__ = ["ChannelRegistry"]
