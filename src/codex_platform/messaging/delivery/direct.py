"""Direct in-process delivery adapter."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from .base import NotificationAdapter

log = logging.getLogger(__name__)


class DirectNotificationAdapter(NotificationAdapter):
    """Adapter for synchronous in-process notification delivery."""

    def __init__(self, config: Any) -> None:
        self.config = config

    def enqueue(self, _task_name: str, payload: dict[str, Any]) -> str | None:
        """Deliver a notification synchronously via the orchestrator pipeline."""

        from codex_platform.messaging.dto import (
            NotificationPayloadDTO,
            RenderedNotificationDTO,
            TemplateNotificationDTO,
        )
        from codex_platform.messaging.orchestrator import BaseDeliveryOrchestrator
        from codex_platform.messaging.registry import ChannelRegistry

        log.debug("DirectNotificationAdapter | starting direct delivery")

        registry = ChannelRegistry()
        _register_default_channels(registry, self.config)
        channels = registry.build_channels(self.config)
        orchestrator = BaseDeliveryOrchestrator(channels=channels)

        payload_dto: NotificationPayloadDTO
        if "html_content" in payload:
            payload_dto = RenderedNotificationDTO(**payload)
        elif "template_name" in payload and "context_key" in payload:
            payload_dto = TemplateNotificationDTO(**payload)
        else:
            payload_dto = NotificationPayloadDTO(**payload)
        asyncio.run(orchestrator.deliver(payload_dto))

        notification_id = payload.get("notification_id")
        log.info("DirectNotificationAdapter | delivered notification_id=%s", notification_id)
        return notification_id


def _register_default_channels(registry: Any, config: Any) -> None:
    """Register default SMTP channel from config when available."""

    try:
        from codex_platform.messaging.clients.smtp import AsyncEmailClient

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
                    smtp_use_tls=getattr(cfg, "SMTP_USE_TLS", False),
                    smtp_from_name=getattr(cfg, "SMTP_FROM_NAME", ""),
                ),
            )
    except ImportError:
        pass


__all__ = ["DirectNotificationAdapter", "_register_default_channels"]
