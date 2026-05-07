"""Framework-agnostic messaging primitives for codex-platform."""

from .audience import AudienceBuilder
from .campaigns import CampaignBatchDTO, CampaignDispatcher, CampaignRecipientDraft
from .channels import NotificationChannel
from .clients.smtp import AsyncEmailClient
from .delivery import ArqNotificationAdapter, DirectNotificationAdapter, NotificationAdapter
from .dto import (
    NotificationPayloadDTO,
    NotificationRecipient,
    RenderedNotificationDTO,
    TemplateNotificationDTO,
    ThreadHeadersDTO,
)
from .interfaces import ContentCacheAdapter, ContentProvider
from .orchestrator import BaseDeliveryOrchestrator, DeliveryChannel
from .registry import ChannelRegistry
from .renderer import TemplateRenderer, resolve_template_path
from .threading import (
    CODEX_THREAD_HEADER,
    LEGACY_LILY_THREAD_HEADER,
    build_message_id,
    build_thread_key,
    parse_references,
    render_email_headers,
    serialize_references,
)
from .workers_contract import (
    PAYLOAD_SCHEMA_VERSION,
    TASK_SEND_CAMPAIGN,
    TASK_SEND_NOTIFICATION,
    TASK_SEND_RENDERED,
)

__all__ = [
    "AudienceBuilder",
    "CampaignBatchDTO",
    "CampaignDispatcher",
    "CampaignRecipientDraft",
    "NotificationChannel",
    "NotificationPayloadDTO",
    "TemplateNotificationDTO",
    "RenderedNotificationDTO",
    "NotificationRecipient",
    "ThreadHeadersDTO",
    "ContentProvider",
    "ContentCacheAdapter",
    "DeliveryChannel",
    "AsyncEmailClient",
    "BaseDeliveryOrchestrator",
    "ChannelRegistry",
    "TemplateRenderer",
    "resolve_template_path",
    "NotificationAdapter",
    "ArqNotificationAdapter",
    "DirectNotificationAdapter",
    "CODEX_THREAD_HEADER",
    "LEGACY_LILY_THREAD_HEADER",
    "build_message_id",
    "build_thread_key",
    "parse_references",
    "render_email_headers",
    "serialize_references",
    "PAYLOAD_SCHEMA_VERSION",
    "TASK_SEND_NOTIFICATION",
    "TASK_SEND_RENDERED",
    "TASK_SEND_CAMPAIGN",
]
