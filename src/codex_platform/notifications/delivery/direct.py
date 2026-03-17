"""
codex_platform.notifications.delivery.direct
=============================================
Direct delivery adapter — delivers notifications synchronously in-process.

Uses the full channel pipeline (ChannelRegistry → BaseDeliveryOrchestrator)
without a message broker.

.. warning::

    Calls ``asyncio.run()`` — MUST NOT be used inside a running event loop
    (ASGI views, async handlers). Use ``ArqNotificationAdapter`` instead.
"""

import asyncio
import logging
from typing import Any

from .base import NotificationAdapter

log = logging.getLogger(__name__)


class DirectNotificationAdapter(NotificationAdapter):
    """
    Adapter for synchronous/monolithic notification delivery.

    Injects a pre-built list of channels (via ``ChannelRegistry``) into
    ``BaseDeliveryOrchestrator`` and runs the async pipeline synchronously.

    Uses lazy imports to avoid circular dependencies.
    """

    def __init__(self, config: Any) -> None:
        self.config = config

    def enqueue(self, _task_name: str, payload: dict[str, Any]) -> str | None:
        """
        Deliver a notification synchronously via the orchestrator pipeline.

        Args:
            _task_name: Unused — direct delivery runs in-process.
            payload:    Serialized ``NotificationPayloadDTO``.

        Returns:
            ``notification_id`` from payload on success, None if not present.

        Raises:
            RuntimeError: If called from within a running event loop.
            Exception: Channel infrastructure failures propagate upward.
        """
        from codex_platform.notifications.dto import NotificationPayloadDTO
        from codex_platform.notifications.orchestrator import BaseDeliveryOrchestrator
        from codex_platform.notifications.registry import ChannelRegistry

        log.debug("DirectNotificationAdapter | starting direct delivery")

        registry = ChannelRegistry()
        _register_default_channels(registry, self.config)
        channels = registry.build_channels(self.config)
        orchestrator = BaseDeliveryOrchestrator(channels=channels)

        payload_dto = NotificationPayloadDTO(**payload)
        asyncio.run(orchestrator.deliver(payload_dto))

        notification_id = payload.get("notification_id")
        log.info("DirectNotificationAdapter | delivered notification_id=%s", notification_id)
        return notification_id


def _register_default_channels(registry: Any, config: Any) -> None:
    """Register default delivery channels from config. Override by calling registry.register() directly."""
    try:
        from codex_platform.notifications.clients.smtp import AsyncEmailClient

        smtp_host = getattr(config, "SMTP_HOST", "")
        if smtp_host:
            registry.register(
                "smtp",
                lambda cfg: AsyncEmailClient(
                    smtp_host=getattr(cfg, "SMTP_HOST", ""),
                    smtp_port=getattr(cfg, "SMTP_PORT", 587),
                    smtp_user=getattr(cfg, "SMTP_USER", None),
                    smtp_password=getattr(cfg, "SMTP_PASSWORD", None),
                    smtp_from_email=getattr(cfg, "SMTP_FROM_EMAIL", None),
                ),
            )
    except ImportError:
        pass
