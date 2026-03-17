"""
codex_platform.adapters.notifications.direct
===========================================
Monolith/Direct adapter — delivers notifications synchronously in-process.

Uses the full channel pipeline (ChannelRegistry → BaseDeliveryOrchestrator)
without a message broker.
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
    ``BaseDeliveryOrchestrator`` and runs the async pipeline synchronously
    via ``asyncio.run()``.

    Uses **lazy imports** to avoid heavy dependencies at import time and
    prevent circular imports in the library.

    .. warning::

        This adapter calls ``asyncio.run()`` which creates a **new** event
        loop.  It **MUST NOT** be called from within an already-running
        event loop (e.g. inside an ASGI view, ``async def`` handler, or
        an asyncio task).  Doing so will raise::

            RuntimeError: asyncio.run() cannot be called from a running event loop

        If your stack is ASGI-based (Uvicorn, Daphne, Hypercorn), use
        ``ArqNotificationAdapter`` to offload to a worker process instead.
    """

    def __init__(self, config: Any):
        self.config = config

    def enqueue(self, _task_name: str, payload: dict[str, Any]) -> str | None:
        """
        Deliver a notification synchronously via the orchestrator pipeline.

        Args:
            _task_name: **Unused.** Direct delivery runs in-process.
                        Accepted for ``NotificationAdapter`` protocol compliance.
            payload: Serialized ``NotificationPayloadDTO``
                     (from ``.model_dump(mode="json")``).

        Returns:
            ``notification_id`` from payload on success, None if not present.

        Raises:
            RuntimeError: If called from within a running event loop.
            Exception: Channel infrastructure failures propagate upward.
        """
        # --- Lazy imports to avoid circular dependencies ---
        from codex_platform.notifications.dto import NotificationPayloadDTO
        from codex_platform.worker.notifications.orchestrator import (
            BaseDeliveryOrchestrator,
        )
        from codex_platform.worker.notifications.registry import ChannelRegistry

        log.debug("DirectNotificationAdapter | starting direct delivery")

        registry = ChannelRegistry()

        # Register channels based on config.
        # Projects can override this pattern by subclassing DirectNotificationAdapter.
        _register_default_channels(registry, self.config)

        channels = registry.build_channels(self.config)
        orchestrator = BaseDeliveryOrchestrator(channels=channels)

        payload_dto = NotificationPayloadDTO(**payload)
        asyncio.run(orchestrator.deliver(payload_dto))

        notification_id = payload.get("notification_id")
        log.info(
            "DirectNotificationAdapter | delivered, notification_id=%s",
            notification_id,
        )
        return notification_id


def _register_default_channels(registry: Any, config: Any) -> None:
    """
    Register the default set of delivery channels from config.

    Projects can call ``registry.register()`` directly for custom channels.
    This helper wires up the Django mail channel when Django is available.
    """
    try:
        from codex_platform.worker.notifications.django_mail import DjangoMailChannel  # lazy

        registry.register(
            "django_mail",
            lambda cfg: DjangoMailChannel(
                from_email=getattr(cfg, "DEFAULT_FROM_EMAIL", None),
            ),
        )
    except ImportError:
        pass  # Django not installed — skip silently

    try:
        from codex_platform.worker.notifications.email import AsyncEmailClient  # lazy

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
        pass  # aiosmtplib not installed — skip silently
