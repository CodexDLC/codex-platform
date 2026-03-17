"""
codex_platform.notifications.dto
==================================
Notification payload contracts.

Three classes:

  NotificationPayloadDTO     — base, always required fields
  TemplateNotificationDTO    — Mode 1: workers fetches context from Redis, renders template
  RenderedNotificationDTO    — Mode 2: pre-rendered HTML (e.g. from Django)
"""

from __future__ import annotations

from codex_core.core import BaseDTO

from .channels import NotificationChannel


class NotificationRecipient(BaseDTO):  # type: ignore[misc]
    """Recipient info. PII fields auto-masked in __repr__ via BaseDTO."""

    email: str | None = None
    phone: str | None = None


class NotificationPayloadDTO(BaseDTO):  # type: ignore[misc]
    """
    Base notification payload — identification and routing only.

    Do not use directly. Use TemplateNotificationDTO or RenderedNotificationDTO.
    """

    notification_id: str
    recipient: NotificationRecipient
    channels: list[NotificationChannel] = [NotificationChannel.EMAIL]
    event_type: str | None = None
    subject: str | None = None


class TemplateNotificationDTO(NotificationPayloadDTO):
    """
    Mode 1 — Worker renders the template itself (requires Jinja2).

    context_key: Redis key where context_data is stored (JSON).
                 Allows updating data after enqueue (e.g. reschedule).
    template_name: Relative template path (e.g. 'booking/bk_confirmation.html').
    """

    template_name: str
    context_key: str


class RenderedNotificationDTO(NotificationPayloadDTO):
    """
    Mode 2 — Pre-rendered HTML passed directly to the workers.

    Use when Django (or another layer) renders the template
    and the workers only needs to deliver.
    """

    html_content: str
    text_content: str | None = None
