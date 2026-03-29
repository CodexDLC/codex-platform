"""Tests for notification delivery adapters and protocols."""

from __future__ import annotations

import asyncio
import sys
from types import ModuleType, SimpleNamespace

import pytest
from pydantic import ValidationError

from codex_platform.notifications.delivery.arq import ArqNotificationAdapter
from codex_platform.notifications.delivery.direct import DirectNotificationAdapter, _register_default_channels

pytestmark = pytest.mark.unit


class FakeArqPool:
    def __init__(self, job=None):
        self.job = job
        self.calls: list[tuple[str, dict]] = []

    async def enqueue_job(self, task_name: str, **kwargs):
        self.calls.append((task_name, kwargs))
        return self.job


class FakeRegistry:
    def __init__(self):
        self.registered: list[tuple[str, object]] = []

    def register(self, name, factory):
        self.registered.append((name, factory))

    def build_channels(self, config):
        self.config = config
        return ["channel"]


class FakeOrchestrator:
    last_channels = None
    delivered_payload = None

    def __init__(self, channels):
        FakeOrchestrator.last_channels = channels

    async def deliver(self, payload):
        FakeOrchestrator.delivered_payload = payload
        return True


class TestArqNotificationAdapter:
    def test_enqueue_wraps_async_version(self, monkeypatch):
        adapter = ArqNotificationAdapter(FakeArqPool())
        expected = "job-1"

        async def fake_enqueue_async(task_name, payload):
            assert task_name == "send_notification"
            assert payload == {"notification_id": "n-1"}
            return expected

        loop = asyncio.new_event_loop()
        self.add_cleanup = loop.close
        monkeypatch.setattr(adapter, "enqueue_async", fake_enqueue_async)
        monkeypatch.setattr("asyncio.get_event_loop", lambda: loop)

        try:
            assert adapter.enqueue("send_notification", {"notification_id": "n-1"}) == expected
        finally:
            loop.close()

    async def test_enqueue_async_returns_job_id(self):
        pool = FakeArqPool(job=SimpleNamespace(job_id="job-123"))
        adapter = ArqNotificationAdapter(pool)

        result = await adapter.enqueue_async("send_notification", {"notification_id": "n-1"})

        assert result == "job-123"
        assert pool.calls == [("send_notification", {"payload_dict": {"notification_id": "n-1"}})]

    async def test_enqueue_async_returns_none_without_job_handle(self):
        pool = FakeArqPool(job=None)
        adapter = ArqNotificationAdapter(pool)

        result = await adapter.enqueue_async("send_notification", {"notification_id": "n-1"})

        assert result is None


class TestDirectNotificationAdapter:
    def test_enqueue_delivers_payload_and_returns_notification_id(self, monkeypatch):
        from asyncio.runners import run as real_asyncio_run

        import codex_platform.notifications.delivery.direct as direct_module

        registry_module = __import__("codex_platform.notifications.registry", fromlist=["ChannelRegistry"])
        orchestrator_module = __import__(
            "codex_platform.notifications.orchestrator",
            fromlist=["BaseDeliveryOrchestrator"],
        )

        monkeypatch.setattr(registry_module, "ChannelRegistry", FakeRegistry)
        monkeypatch.setattr(orchestrator_module, "BaseDeliveryOrchestrator", FakeOrchestrator)
        monkeypatch.setattr(direct_module, "_register_default_channels", lambda registry, config: None)
        monkeypatch.setattr(direct_module.asyncio, "run", real_asyncio_run)

        adapter = DirectNotificationAdapter(SimpleNamespace(SMTP_HOST="smtp.example.com"))
        payload = {
            "notification_id": "n-1",
            "recipient": {"email": "user@example.com"},
            "channels": ["email"],
            "subject": "Hello",
            "html_content": "<p>Hello</p>",
        }

        result = adapter.enqueue("ignored_task_name", payload)

        assert result == "n-1"
        assert FakeOrchestrator.last_channels == ["channel"]
        assert FakeOrchestrator.delivered_payload.notification_id == "n-1"

    def test_enqueue_returns_none_when_fake_payload_omits_notification_id(self, monkeypatch):
        from asyncio.runners import run as real_asyncio_run

        import codex_platform.notifications.delivery.direct as direct_module

        dto_module = __import__("codex_platform.notifications.dto", fromlist=["NotificationPayloadDTO"])
        registry_module = __import__("codex_platform.notifications.registry", fromlist=["ChannelRegistry"])
        orchestrator_module = __import__(
            "codex_platform.notifications.orchestrator",
            fromlist=["BaseDeliveryOrchestrator"],
        )

        class FakePayloadDTO:
            def __init__(self, **payload):
                self.recipient = SimpleNamespace(email=payload["recipient"]["email"])
                self.subject = payload.get("subject")
                self.html_content = payload.get("html_content")
                self.text_content = payload.get("text_content")
                self.notification_id = payload.get("notification_id")

        monkeypatch.setattr(dto_module, "NotificationPayloadDTO", FakePayloadDTO)
        monkeypatch.setattr(registry_module, "ChannelRegistry", FakeRegistry)
        monkeypatch.setattr(orchestrator_module, "BaseDeliveryOrchestrator", FakeOrchestrator)
        monkeypatch.setattr(direct_module, "_register_default_channels", lambda registry, config: None)
        monkeypatch.setattr(direct_module.asyncio, "run", real_asyncio_run)

        adapter = DirectNotificationAdapter(SimpleNamespace(SMTP_HOST="smtp.example.com"))
        payload = {
            "notification_id": None,
            "recipient": {"email": "user@example.com"},
            "channels": ["email"],
            "subject": "Hello",
            "html_content": "<p>Hello</p>",
        }

        assert adapter.enqueue("ignored_task_name", payload) is None

    def test_enqueue_raises_validation_error_for_invalid_payload(self):
        adapter = DirectNotificationAdapter(SimpleNamespace(SMTP_HOST="smtp.example.com"))

        with pytest.raises(ValidationError):
            adapter.enqueue(
                "ignored_task_name",
                {
                    "recipient": {"email": "user@example.com"},
                    "channels": ["email"],
                },
            )


class TestRegisterDefaultChannels:
    def test_registers_smtp_when_host_present(self, monkeypatch):
        fake_module = ModuleType("codex_platform.notifications.clients.smtp")

        class FakeAsyncEmailClient:
            def __init__(self, **kwargs):
                self.kwargs = kwargs

        fake_module.AsyncEmailClient = FakeAsyncEmailClient
        monkeypatch.setitem(sys.modules, "codex_platform.notifications.clients.smtp", fake_module)

        registry = FakeRegistry()
        config = SimpleNamespace(
            SMTP_HOST="smtp.example.com",
            SMTP_PORT=2525,
            SMTP_USER="user",
            SMTP_PASSWORD="secret",  # pragma: allowlist secret
            SMTP_FROM_EMAIL="noreply@example.com",
        )

        _register_default_channels(registry, config)

        assert len(registry.registered) == 1
        name, factory = registry.registered[0]
        assert name == "smtp"
        client = factory(config)
        assert client.kwargs["smtp_host"] == "smtp.example.com"
        assert client.kwargs["smtp_port"] == 2525

    def test_skips_registration_when_host_missing(self):
        registry = FakeRegistry()
        config = SimpleNamespace(SMTP_HOST="")

        _register_default_channels(registry, config)

        assert registry.registered == []

    def test_ignores_missing_smtp_dependency(self, monkeypatch):
        monkeypatch.delitem(sys.modules, "codex_platform.notifications.clients.smtp", raising=False)

        original_import = __import__

        def fake_import(name, *args, **kwargs):
            if name == "codex_platform.notifications.clients.smtp":
                raise ImportError("missing smtp client")
            return original_import(name, *args, **kwargs)

        monkeypatch.setattr("builtins.__import__", fake_import)
        registry = FakeRegistry()

        _register_default_channels(registry, SimpleNamespace(SMTP_HOST="smtp.example.com"))

        assert registry.registered == []


def test_notification_adapter_protocol_shape():
    class DummyAdapter:
        def enqueue(self, task_name, payload):
            return payload.get("notification_id")

    adapter = DummyAdapter()

    assert callable(adapter.enqueue)
