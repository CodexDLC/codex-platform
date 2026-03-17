"""Tests for codex_platform.notifications.orchestrator."""

from dataclasses import dataclass, field

from codex_platform.notifications.orchestrator import BaseDeliveryOrchestrator

import pytest
pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# Mock helpers (no dependency on codex_core)
# ---------------------------------------------------------------------------
@dataclass
class MockRecipient:
    email: str | None = None
    phone: str | None = None


@dataclass
class MockPayload:
    notification_id: str = "test-1"
    recipient: MockRecipient = field(
        default_factory=lambda: MockRecipient(email="test@example.com"),
    )
    subject: str = "Test"
    html_content: str = "<p>Hello</p>"
    text_content: str | None = None


class FakeChannel:
    """A fake delivery channel for testing."""

    def __init__(self, *, available: bool = True, succeeds: bool = True, raises: Exception | None = None):
        self._available = available
        self._succeeds = succeeds
        self._raises = raises
        self.send_called = False
        self.send_args: dict | None = None

    def is_available(self) -> bool:
        return self._available

    async def send(self, to: str, subject: str, html_content: str | None, text_content: str | None) -> bool:
        self.send_called = True
        self.send_args = {"to": to, "subject": subject, "html_content": html_content, "text_content": text_content}
        if self._raises:
            raise self._raises
        return self._succeeds


class TestBaseDeliveryOrchestrator:
    async def test_deliver_first_success(self):
        ch1 = FakeChannel(succeeds=True)
        ch2 = FakeChannel(succeeds=True)
        orch = BaseDeliveryOrchestrator(channels=[ch1, ch2])

        result = await orch.deliver(MockPayload())

        assert result is True
        assert ch1.send_called
        assert not ch2.send_called  # stopped after first success

    async def test_deliver_skips_unavailable(self):
        ch1 = FakeChannel(available=False)
        ch2 = FakeChannel(succeeds=True)
        orch = BaseDeliveryOrchestrator(channels=[ch1, ch2])

        result = await orch.deliver(MockPayload())

        assert result is True
        assert not ch1.send_called
        assert ch2.send_called

    async def test_deliver_no_recipient_returns_false(self):
        ch = FakeChannel(succeeds=True)
        orch = BaseDeliveryOrchestrator(channels=[ch])
        payload = MockPayload(recipient=MockRecipient())  # no email, no phone

        result = await orch.deliver(payload)

        assert result is False
        assert not ch.send_called

    async def test_deliver_all_fail_returns_false(self):
        ch1 = FakeChannel(succeeds=False)
        ch2 = FakeChannel(succeeds=False)
        orch = BaseDeliveryOrchestrator(channels=[ch1, ch2])

        result = await orch.deliver(MockPayload())

        assert result is False
        assert ch1.send_called
        assert ch2.send_called

    async def test_deliver_channel_raises_tries_next(self):
        ch1 = FakeChannel(raises=RuntimeError("SMTP down"))
        ch2 = FakeChannel(succeeds=True)
        orch = BaseDeliveryOrchestrator(channels=[ch1, ch2])

        result = await orch.deliver(MockPayload())

        assert result is True
        assert ch1.send_called
        assert ch2.send_called

    async def test_deliver_uses_phone_when_no_email(self):
        ch = FakeChannel(succeeds=True)
        orch = BaseDeliveryOrchestrator(channels=[ch])
        payload = MockPayload(recipient=MockRecipient(phone="+1234567890"))

        result = await orch.deliver(payload)

        assert result is True
        assert ch.send_args["to"] == "+1234567890"

    async def test_deliver_empty_channels_returns_false(self):
        orch = BaseDeliveryOrchestrator(channels=[])

        result = await orch.deliver(MockPayload())

        assert result is False

    async def test_deliver_all_unavailable_returns_false(self):
        ch1 = FakeChannel(available=False)
        ch2 = FakeChannel(available=False)
        orch = BaseDeliveryOrchestrator(channels=[ch1, ch2])

        result = await orch.deliver(MockPayload())

        assert result is False
