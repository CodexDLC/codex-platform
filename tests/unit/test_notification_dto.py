"""Tests for codex_platform.notifications.dto."""

import pytest

try:
    from codex_platform.notifications.channels import NotificationChannel
    from codex_platform.notifications.dto import (
        NotificationPayloadDTO,
        NotificationRecipient,
        RenderedNotificationDTO,
        TemplateNotificationDTO,
    )

    SKIP = False
except ImportError:
    SKIP = True

pytestmark = [pytest.mark.unit, pytest.mark.skipif(SKIP, reason="codex-core not installed")]


class TestNotificationRecipient:
    def test_defaults_to_none(self):
        r = NotificationRecipient()
        assert r.email is None
        assert r.phone is None

    def test_accepts_email(self):
        r = NotificationRecipient(email="a@b.com")
        assert r.email == "a@b.com"
        assert r.phone is None

    def test_accepts_phone(self):
        r = NotificationRecipient(phone="+1234567890")
        assert r.phone == "+1234567890"

    def test_accepts_both(self):
        r = NotificationRecipient(email="a@b.com", phone="+1234567890")
        assert r.email == "a@b.com"
        assert r.phone == "+1234567890"


class TestNotificationPayloadDTO:
    def test_required_fields(self):
        recipient = NotificationRecipient(email="a@b.com")
        dto = NotificationPayloadDTO(notification_id="n-1", recipient=recipient)
        assert dto.notification_id == "n-1"
        assert dto.recipient.email == "a@b.com"

    def test_default_channels(self):
        dto = NotificationPayloadDTO(
            notification_id="n-1",
            recipient=NotificationRecipient(),
        )
        assert dto.channels == [NotificationChannel.EMAIL]

    def test_custom_channels(self):
        dto = NotificationPayloadDTO(
            notification_id="n-1",
            recipient=NotificationRecipient(),
            channels=[NotificationChannel.SMS, NotificationChannel.TELEGRAM],
        )
        assert NotificationChannel.SMS in dto.channels
        assert NotificationChannel.TELEGRAM in dto.channels

    def test_optional_fields_default_none(self):
        dto = NotificationPayloadDTO(
            notification_id="n-1",
            recipient=NotificationRecipient(),
        )
        assert dto.event_type is None
        assert dto.subject is None

    def test_missing_notification_id_raises(self):
        with pytest.raises(ValueError):  # ValidationError
            NotificationPayloadDTO(recipient=NotificationRecipient())

    def test_missing_recipient_raises(self):
        with pytest.raises(ValueError):  # ValidationError
            NotificationPayloadDTO(notification_id="n-1")


class TestTemplateNotificationDTO:
    def test_required_fields(self):
        dto = TemplateNotificationDTO(
            notification_id="n-1",
            recipient=NotificationRecipient(email="a@b.com"),
            template_name="booking/confirm.html",
            context_key="redis:ctx:123",
        )
        assert dto.template_name == "booking/confirm.html"
        assert dto.context_key == "redis:ctx:123"

    def test_missing_template_name_raises(self):
        with pytest.raises(ValueError):
            TemplateNotificationDTO(
                notification_id="n-1",
                recipient=NotificationRecipient(),
                context_key="redis:ctx:123",
            )

    def test_missing_context_key_raises(self):
        with pytest.raises(ValueError):
            TemplateNotificationDTO(
                notification_id="n-1",
                recipient=NotificationRecipient(),
                template_name="booking/confirm.html",
            )


class TestRenderedNotificationDTO:
    def test_required_fields(self):
        dto = RenderedNotificationDTO(
            notification_id="n-1",
            recipient=NotificationRecipient(email="a@b.com"),
            html_content="<p>Hello</p>",
        )
        assert dto.html_content == "<p>Hello</p>"
        assert dto.text_content is None

    def test_with_text_content(self):
        dto = RenderedNotificationDTO(
            notification_id="n-1",
            recipient=NotificationRecipient(),
            html_content="<p>Hi</p>",
            text_content="Hi",
        )
        assert dto.text_content == "Hi"

    def test_missing_html_content_raises(self):
        with pytest.raises(ValueError):
            RenderedNotificationDTO(
                notification_id="n-1",
                recipient=NotificationRecipient(),
            )
