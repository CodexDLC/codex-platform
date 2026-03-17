"""Tests for codex_platform.notifications.channels."""

import sys
from enum import Enum

if sys.version_info >= (3, 11):
    from enum import StrEnum
else:
    # Fallback for Python 3.10
    class StrEnum(str, Enum):
        pass


import pytest

from codex_platform.notifications.channels import NotificationChannel

pytestmark = pytest.mark.unit


class TestNotificationChannel:
    def test_is_str_enum(self):
        # On Python 3.11+ this is enum.StrEnum.
        # On Python 3.10 this is our fallback StrEnum which is just (str, Enum).
        if sys.version_info >= (3, 11):
            assert issubclass(NotificationChannel, StrEnum)
        else:
            assert issubclass(NotificationChannel, str)
            assert issubclass(NotificationChannel, Enum)

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
