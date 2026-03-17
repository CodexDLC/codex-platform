"""
codex_platform.notifications
=============================
Building blocks for notification delivery.

    # Contracts / DTOs
    from codex_platform.notifications import NotificationPayloadDTO, NotificationRecipient
    from codex_platform.notifications import NotificationChannel

    # Channel pipeline
    from codex_platform.notifications import AsyncEmailClient
    from codex_platform.notifications import BaseDeliveryOrchestrator, ChannelRegistry

    # Delivery adapters (how payload gets to the pipeline)
    from codex_platform.notifications.delivery import ArqNotificationAdapter
    from codex_platform.notifications.delivery import DirectNotificationAdapter

    # Template rendering (requires jinja2 — install separately)
    from codex_platform.notifications.renderer import TemplateRenderer
"""

from .channels import NotificationChannel
from .clients.smtp import AsyncEmailClient
from .delivery import ArqNotificationAdapter, DirectNotificationAdapter, NotificationAdapter
from .dto import NotificationPayloadDTO, NotificationRecipient, RenderedNotificationDTO, TemplateNotificationDTO
from .interfaces import ContentCacheAdapter, ContentProvider
from .orchestrator import BaseDeliveryOrchestrator, DeliveryChannel
from .registry import ChannelRegistry

__all__ = [
    # Contracts
    "NotificationChannel",
    "NotificationPayloadDTO",
    "TemplateNotificationDTO",
    "RenderedNotificationDTO",
    "NotificationRecipient",
    "ContentProvider",
    "ContentCacheAdapter",
    "DeliveryChannel",
    # Channel pipeline
    "AsyncEmailClient",
    "BaseDeliveryOrchestrator",
    "ChannelRegistry",
    # Delivery adapters
    "NotificationAdapter",
    "ArqNotificationAdapter",
    "DirectNotificationAdapter",
]
