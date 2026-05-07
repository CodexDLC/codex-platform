"""Messaging payload contracts."""

from __future__ import annotations

from codex_core.core import BaseDTO

from .channels import NotificationChannel
from .workers_contract import PAYLOAD_SCHEMA_VERSION


class ThreadHeadersDTO(BaseDTO):
    """RFC 5322 threading headers attached to outbound email notifications."""

    message_id: str
    in_reply_to: str | None = None
    references: list[str] = []
    thread_key: str
    reply_match_token: str | None = None


class NotificationRecipient(BaseDTO):
    """Recipient info. PII fields auto-masked in ``repr`` via BaseDTO."""

    email: str | None = None
    phone: str | None = None


class NotificationPayloadDTO(BaseDTO):
    """Base notification payload: identification and routing only."""

    schema_version: int = PAYLOAD_SCHEMA_VERSION
    notification_id: str
    recipient: NotificationRecipient
    channels: list[NotificationChannel] = [NotificationChannel.EMAIL]
    event_type: str | None = None
    subject: str | None = None
    headers: ThreadHeadersDTO | None = None


class TemplateNotificationDTO(NotificationPayloadDTO):
    """Mode 1: worker fetches context from Redis and renders the template."""

    template_name: str
    context_key: str


class RenderedNotificationDTO(NotificationPayloadDTO):
    """Mode 2: pre-rendered HTML passed directly to the worker."""

    html_content: str
    text_content: str | None = None


__all__ = [
    "ThreadHeadersDTO",
    "NotificationRecipient",
    "NotificationPayloadDTO",
    "TemplateNotificationDTO",
    "RenderedNotificationDTO",
]
