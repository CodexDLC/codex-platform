"""Tests for codex_platform.messaging public API additions."""

from __future__ import annotations

import pathlib
from email.message import EmailMessage
from unittest.mock import AsyncMock, patch

import pytest

from codex_platform.messaging import (
    PAYLOAD_SCHEMA_VERSION,
    TASK_SEND_CAMPAIGN,
    TASK_SEND_NOTIFICATION,
    TASK_SEND_RENDERED,
    AsyncEmailClient,
    CampaignBatchDTO,
    CampaignRecipientDraft,
    NotificationPayloadDTO,
    NotificationRecipient,
    RenderedNotificationDTO,
    ThreadHeadersDTO,
    build_message_id,
    build_thread_key,
    parse_references,
    render_email_headers,
    resolve_template_path,
    serialize_references,
)
from codex_platform.messaging.channels import NotificationChannel
from codex_platform.messaging.orchestrator import BaseDeliveryOrchestrator

pytestmark = pytest.mark.unit


def test_notification_payload_has_schema_version_and_headers():
    headers = ThreadHeadersDTO(message_id="<m@example.com>", thread_key="tk_1")
    dto = NotificationPayloadDTO(
        notification_id="n-1",
        recipient=NotificationRecipient(email="user@example.com"),
        headers=headers,
    )

    assert dto.schema_version == PAYLOAD_SCHEMA_VERSION
    assert dto.headers == headers
    assert dto.channels == [NotificationChannel.EMAIL]


def test_campaign_batch_requires_exactly_one_rendering_mode():
    recipient = CampaignRecipientDraft(recipient_id="1", email="user@example.com")

    dto = CampaignBatchDTO(
        campaign_id="c-1",
        template_name="mk_basic",
        subject="Hello",
        recipients=[recipient],
        callback_url="https://example.com/callback",
        callback_token="token",
    )

    assert dto.schema_version == PAYLOAD_SCHEMA_VERSION

    with pytest.raises(ValueError):
        CampaignBatchDTO(
            campaign_id="c-1",
            subject="Hello",
            recipients=[recipient],
            callback_url="https://example.com/callback",
            callback_token="token",
        )


def test_threading_helpers_render_expected_headers():
    message_id = build_message_id(domain="mail.example.com")
    thread_key = build_thread_key()
    references = ["<a@example.com>", "<b@example.com>"]

    assert message_id.startswith("<") and message_id.endswith("@mail.example.com>")
    assert thread_key.startswith("tk_")
    assert parse_references(serialize_references(references)) == references

    headers = render_email_headers(
        ThreadHeadersDTO(
            message_id="<c@example.com>",
            in_reply_to="<b@example.com>",
            references=references,
            thread_key="tk_test",
        )
    )

    assert headers["Message-ID"] == "<c@example.com>"
    assert headers["In-Reply-To"] == "<b@example.com>"
    assert headers["References"] == "<a@example.com> <b@example.com>"
    assert headers["X-Codex-Thread-Key"] == "tk_test"
    assert headers["X-Lily-Thread-Key"] == "tk_test"


def test_resolve_template_path_uses_default_prefixes():
    assert resolve_template_path("bk_confirmation") == "booking/bk_confirmation.html"
    assert resolve_template_path("contacts/custom.html") == "contacts/custom.html"
    assert resolve_template_path("welcome") == "welcome.html"


def test_worker_contract_constants():
    assert PAYLOAD_SCHEMA_VERSION == 1
    assert TASK_SEND_NOTIFICATION == "send_universal_notification_task"
    assert TASK_SEND_RENDERED == "send_rendered_notification_task"
    assert TASK_SEND_CAMPAIGN == "send_campaign_batch_task"


async def test_orchestrator_passes_thread_headers_to_channel():
    class FakeChannel:
        def __init__(self):
            self.kwargs = None

        def is_available(self):
            return True

        async def send(self, **kwargs):
            self.kwargs = kwargs
            return True

    channel = FakeChannel()
    headers = ThreadHeadersDTO(message_id="<m@example.com>", thread_key="tk_1")
    payload = RenderedNotificationDTO(
        notification_id="n-1",
        recipient=NotificationRecipient(email="user@example.com"),
        subject="Subject",
        html_content="<p>Hello</p>",
        headers=headers,
    )

    result = await BaseDeliveryOrchestrator([channel]).deliver(payload)

    assert result is True
    assert channel.kwargs["headers"] == headers


async def test_smtp_client_applies_thread_headers():
    headers = ThreadHeadersDTO(message_id="<m@example.com>", thread_key="tk_1")
    client = AsyncEmailClient(
        smtp_host="mail.example.com",
        smtp_port=587,
        smtp_from_email="noreply@example.com",
        smtp_from_name="Codex",
    )

    sent_message: EmailMessage | None = None

    async def fake_send(message, **_kwargs):
        nonlocal sent_message
        sent_message = message

    with patch("codex_platform.messaging.clients.smtp.aiosmtplib") as mock_aiosmtplib:
        mock_aiosmtplib.send = AsyncMock(side_effect=fake_send)
        await client.send(
            to="user@example.com",
            subject="Subject",
            html_content="<p>Hello</p>",
            text_content="Hello",
            headers=headers,
        )

    assert sent_message is not None
    assert sent_message["From"] == "Codex <noreply@example.com>"
    assert sent_message["Message-ID"] == "<m@example.com>"
    assert sent_message["X-Codex-Thread-Key"] == "tk_1"


def test_notifications_imports_reexport_messaging_symbols():
    from codex_platform.messaging import NotificationPayloadDTO as NewPayload
    from codex_platform.notifications import NotificationPayloadDTO as OldPayload

    assert OldPayload is NewPayload


def test_messaging_package_does_not_import_django():
    root = pathlib.Path(__file__).parents[2] / "src" / "codex_platform" / "messaging"
    offenders = []
    for path in root.rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        if "import django" in text or "codex_django" in text:
            offenders.append(path.relative_to(root).as_posix())

    assert offenders == []
