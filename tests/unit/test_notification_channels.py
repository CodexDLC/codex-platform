"""Tests for codex_platform.notifications.channels."""

from enum import StrEnum

import pytest

from codex_platform.notifications.channels import NotificationChannel

pytestmark = pytest.mark.unit


class TestNotificationChannel:
    def test_is_str_enum(self):
        assert issubclass(NotificationChannel, StrEnum)

    def test_has_email(self):
        assert NotificationChannel.EMAIL == "email"

    def test_has_telegram(self):
        assert NotificationChannel.TELEGRAM == "telegram"

    def test_has_sms(self):
        assert NotificationChannel.SMS == "sms"

    def test_has_whatsapp(self):
        assert NotificationChannel.WHATSAPP == "whatsapp"

    def test_members_count(self):
        assert len(NotificationChannel) == 4

    def test_str_value(self):
        # StrEnum members are also strings
        assert isinstance(NotificationChannel.EMAIL, str)
        assert f"{NotificationChannel.EMAIL}" == "email"
