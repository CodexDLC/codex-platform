"""
codex_platform.worker.notifications.email
========================================
Async SMTP email client — implements ``DeliveryChannel``.

Creates persistent SMTP connection config at init time.
For multi-tenant: create separate instances with different settings.

Requires: pip install codex-tools[notifications]
"""

import logging
from email.message import EmailMessage
from typing import Any

log = logging.getLogger(__name__)

try:
    import aiosmtplib

    _AIOSMTP_AVAILABLE = True
except ImportError as e:
    if e.name == "aiosmtplib":
        _AIOSMTP_AVAILABLE = False
    else:
        raise


class AsyncEmailClient:
    """
    Async SMTP email sender. Implements ``DeliveryChannel``.

    Usage:
        client = AsyncEmailClient(
            smtp_host="mail.example.com", smtp_port=465,
            smtp_user="user", smtp_password="pass",  # pragma: allowlist secret
            smtp_from_email="noreply@example.com",
        )
        success = await client.send(
            to="user@example.com",
            subject="Hello",
            html_content="<b>Hi</b>",
            text_content="Hi",
        )
    """

    def __init__(
        self,
        smtp_host: str,
        smtp_port: int,
        smtp_user: str | None = None,
        smtp_password: str | None = None,  # pragma: allowlist secret
        smtp_from_email: str | None = None,
        smtp_use_tls: bool = False,
    ) -> None:
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port
        self.smtp_user = smtp_user
        self.smtp_password = smtp_password
        self.smtp_from_email = smtp_from_email
        self.smtp_use_tls = smtp_use_tls

    def is_available(self) -> bool:
        """Returns True if the client is configured (non-localhost host)."""
        return bool(self.smtp_host and self.smtp_host != "localhost")

    async def send(
        self,
        to: str,
        subject: str,
        html_content: str | None,
        text_content: str | None,
        timeout: int = 15,
    ) -> bool:
        """
        Send email via SMTP.

        Args:
            to: Recipient email address.
            subject: Email subject line.
            html_content: HTML body (preferred). Used as HTML part.
            text_content: Plain-text body (fallback for HTML-disabled clients).
                          If None and html_content is provided, a generic fallback
                          is used.
            timeout: SMTP connection timeout in seconds.

        Returns:
            True on success.

        Raises:
            RuntimeError: If aiosmtplib is not installed.
            aiosmtplib.SMTPException: On SMTP delivery failure.
        """
        if not _AIOSMTP_AVAILABLE:
            raise RuntimeError("aiosmtplib not installed. Run: pip install codex-tools[notifications]")
        await self._send_smtp(to, subject, html_content, text_content, timeout)
        log.info("AsyncEmailClient | sent to='%s'", to)
        return True

    async def _send_smtp(
        self,
        to: str,
        subject: str,
        html_content: str | None,
        text_content: str | None,
        timeout: int,
    ) -> None:
        message = EmailMessage()
        message["From"] = self.smtp_from_email
        message["To"] = to
        message["Subject"] = subject

        plain = text_content or "Please enable HTML to view this email."
        message.set_content(plain)

        if html_content:
            message.add_alternative(html_content, subtype="html")

        use_ssl = self.smtp_port == 465
        start_tls = self.smtp_port == 587 or (self.smtp_use_tls and self.smtp_port != 465)

        send_kwargs: dict[str, Any] = {
            "hostname": self.smtp_host,
            "port": self.smtp_port,
            "use_tls": use_ssl,
            "start_tls": start_tls,
            "timeout": timeout,
        }

        if self.smtp_user and self.smtp_password:
            send_kwargs["username"] = self.smtp_user
            send_kwargs["password"] = self.smtp_password

        await aiosmtplib.send(message, **send_kwargs)
