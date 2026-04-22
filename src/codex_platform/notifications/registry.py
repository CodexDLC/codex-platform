"""
codex_platform.notifications.channels.registry
=============================================
Auto-discovers available delivery channels based on configuration.

Usage:
    registry = ChannelRegistry()
    registry.register("smtp", lambda cfg: SmtpChannel(cfg) if cfg.SMTP_HOST else None)
    registry.register("sendgrid", lambda cfg: SendGridChannel(cfg) if cfg.SENDGRID_API_KEY else None)
    channels = registry.build_channels(settings)
    # → [SmtpChannel, SendGridChannel]  (only those whose config is populated)
"""

import logging
from collections.abc import Callable
from typing import Any

from .orchestrator import DeliveryChannel

log = logging.getLogger(__name__)


class ChannelRegistry:
    """
    Registry for delivery channels.
    Channels register with a factory function that returns a channel or None.
    build_channels() creates only the channels whose config is available.
    """

    def __init__(self) -> None:
        self._factories: list[tuple[str, Callable[[Any], DeliveryChannel | None]]] = []

    def register(
        self,
        name: str,
        factory: Callable[[Any], DeliveryChannel | None],
    ) -> None:
        """
        Register a channel factory.

        Args:
            name: Human-readable channel name (for logging).
            factory: Callable that takes config and returns DeliveryChannel or None.
                     Return None if the channel's config is missing/incomplete.
        """
        self._factories.append((name, factory))

    def build_channels(self, config: Any) -> list[DeliveryChannel]:
        """Build the list of available channels from all registered factories.

        Calls each factory with ``config``. A channel is included only when the
        factory returns a non-``None`` instance that also reports ``is_available() == True``.

        Args:
            config: Application settings object passed verbatim to every factory.

        Returns:
            Ordered list of ready-to-use :class:`DeliveryChannel` instances.
        """
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
