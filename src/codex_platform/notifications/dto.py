"""
codex_platform.notifications.dto
==============================
Unified notification payload contract.

All notification channels expect this format.
The caller is responsible for rendering html_content / text_content
before passing the DTO — this library does NOT render templates.
"""

from __future__ import annotations

from pydantic import Field

from codex_platform.core.base_dto import BaseDTO


class NotificationRecipient(BaseDTO):
    """Recipient info. PII fields auto-masked in __repr__ via BaseDTO."""

    email: str | None = None
    phone: str | None = None


class NotificationPayloadDTO(BaseDTO):
    """
    Unified notification payload — the single contract for all channels.

    The caller prepares html_content and text_content before dispatching.
    The library delivers what it receives — no rendering, no DB lookups.
    """

    notification_id: str
    recipient: NotificationRecipient
    event_type: str | None = None
    subject: str | None = None
    html_content: str | None = None
    text_content: str | None = None
    channels: list[str] = Field(default_factory=lambda: ["email"])
