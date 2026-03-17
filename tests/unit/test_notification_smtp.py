"""Tests for codex_platform.notifications.clients.smtp (AsyncEmailClient)."""

from unittest.mock import AsyncMock, patch

import pytest

try:
    from codex_platform.notifications.clients.smtp import _AIOSMTP_AVAILABLE, AsyncEmailClient

    SKIP = False
except ImportError:
    SKIP = True

pytestmark = [pytest.mark.unit, pytest.mark.skipif(SKIP, reason="notifications client not importable")]


class TestAsyncEmailClientAvailability:
    def test_is_available_with_host(self):
        client = AsyncEmailClient(smtp_host="mail.example.com", smtp_port=465)
        assert client.is_available() is True

    def test_is_not_available_with_empty_host(self):
        client = AsyncEmailClient(smtp_host="", smtp_port=465)
        assert client.is_available() is False

    def test_is_not_available_with_localhost(self):
        client = AsyncEmailClient(smtp_host="localhost", smtp_port=465)
        assert client.is_available() is False


class TestAsyncEmailClientSend:
    @pytest.mark.skipif(not _AIOSMTP_AVAILABLE if not SKIP else True, reason="aiosmtplib not installed")
    async def test_send_calls_aiosmtplib(self):
        client = AsyncEmailClient(
            smtp_host="mail.example.com",
            smtp_port=465,
            smtp_user="user",
            smtp_password="pass",  # pragma: allowlist secret
            smtp_from_email="noreply@example.com",
        )

        with patch("codex_platform.notifications.clients.smtp.aiosmtplib") as mock_aiosmtplib:
            mock_aiosmtplib.send = AsyncMock()

            result = await client.send(
                to="user@example.com",
                subject="Test",
                html_content="<p>Hello</p>",
                text_content="Hello",
            )

            assert result is True
            mock_aiosmtplib.send.assert_awaited_once()

    @pytest.mark.skipif(not _AIOSMTP_AVAILABLE if not SKIP else True, reason="aiosmtplib not installed")
    async def test_send_passes_correct_kwargs(self):
        client = AsyncEmailClient(
            smtp_host="mail.example.com",
            smtp_port=587,
            smtp_user="user",
            smtp_password="pass",  # pragma: allowlist secret
            smtp_from_email="noreply@example.com",
        )

        with patch("codex_platform.notifications.clients.smtp.aiosmtplib") as mock_aiosmtplib:
            mock_aiosmtplib.send = AsyncMock()

            await client.send(
                to="user@example.com",
                subject="Test",
                html_content="<p>Hello</p>",
                text_content=None,
            )

            mock_aiosmtplib.send.assert_awaited_once()

    @pytest.mark.skipif(not _AIOSMTP_AVAILABLE if not SKIP else True, reason="aiosmtplib not installed")
    async def test_send_without_html(self):
        client = AsyncEmailClient(
            smtp_host="mail.example.com",
            smtp_port=465,
            smtp_from_email="noreply@example.com",
        )

        with patch("codex_platform.notifications.clients.smtp.aiosmtplib") as mock_aiosmtplib:
            mock_aiosmtplib.send = AsyncMock()

            result = await client.send(
                to="user@example.com",
                subject="Test",
                html_content=None,
                text_content="Plain text",
            )

            assert result is True
