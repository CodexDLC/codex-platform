"""Tests for codex_platform.notifications.registry."""

from codex_platform.notifications.registry import ChannelRegistry

import pytest
pytestmark = pytest.mark.unit


class FakeChannel:
    def __init__(self, *, available: bool = True):
        self._available = available

    def is_available(self) -> bool:
        return self._available

    async def send(self, to, subject, html_content, text_content) -> bool:
        return True


class TestChannelRegistry:
    def test_register_adds_factory(self):
        reg = ChannelRegistry()
        reg.register("smtp", lambda cfg: FakeChannel())
        # Internal check: one factory registered
        assert len(reg._factories) == 1

    def test_build_channels_calls_factories(self):
        reg = ChannelRegistry()
        reg.register("smtp", lambda cfg: FakeChannel())
        reg.register("telegram", lambda cfg: FakeChannel())

        channels = reg.build_channels(config={})

        assert len(channels) == 2

    def test_build_channels_skips_none(self):
        reg = ChannelRegistry()
        reg.register("smtp", lambda cfg: FakeChannel())
        reg.register("disabled", lambda cfg: None)

        channels = reg.build_channels(config={})

        assert len(channels) == 1

    def test_build_channels_skips_unavailable(self):
        reg = ChannelRegistry()
        reg.register("smtp", lambda cfg: FakeChannel(available=True))
        reg.register("broken", lambda cfg: FakeChannel(available=False))

        channels = reg.build_channels(config={})

        assert len(channels) == 1

    def test_build_channels_catches_factory_exceptions(self):
        def bad_factory(cfg):
            raise ValueError("misconfigured")

        reg = ChannelRegistry()
        reg.register("good", lambda cfg: FakeChannel())
        reg.register("bad", bad_factory)

        channels = reg.build_channels(config={})

        assert len(channels) == 1

    def test_build_channels_passes_config(self):
        received = {}

        def factory(cfg):
            received["cfg"] = cfg
            return FakeChannel()

        reg = ChannelRegistry()
        reg.register("smtp", factory)

        config = {"SMTP_HOST": "mail.example.com"}
        reg.build_channels(config=config)

        assert received["cfg"] is config

    def test_build_channels_empty_registry(self):
        reg = ChannelRegistry()
        assert reg.build_channels(config={}) == []
