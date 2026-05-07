"""Async SMTP email client implementing the messaging delivery channel."""

from __future__ import annotations

import logging
from email.message import EmailMessage
from email.utils import formataddr
from typing import Any

from codex_platform.messaging.dto import ThreadHeadersDTO
from codex_platform.messaging.threading import render_email_headers

log = logging.getLogger(__name__)

try:
    import aiosmtplib

    _AIOSMTP_AVAILABLE = True
except ImportError as e:
    if e.name == "aiosmtplib":
        aiosmtplib = None  # type: ignore[assignment]
        _AIOSMTP_AVAILABLE = False
    else:
        raise


class AsyncEmailClient:
    """Async SMTP email sender."""

    def __init__(
        self,
        smtp_host: str,
        smtp_port: int,
        smtp_user: str | None = None,
        smtp_password: str | None = None,  # pragma: allowlist secret
        smtp_from_email: str | None = None,
        smtp_use_tls: bool = False,
        smtp_from_name: str = "",
    ) -> None:
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port
        self.smtp_user = smtp_user
        self.smtp_password = smtp_password
        self.smtp_from_email = smtp_from_email
        self.smtp_use_tls = smtp_use_tls
        self.smtp_from_name = smtp_from_name

    def is_available(self) -> bool:
        """Returns True if the client is configured with a non-localhost host."""

        return bool(self.smtp_host and self.smtp_host != "localhost")

    async def send(
        self,
        to: str,
        subject: str,
        html_content: str | None,
        text_content: str | None,
        headers: ThreadHeadersDTO | None = None,
        timeout: int = 15,
    ) -> bool:
        """Send email via SMTP."""

        if not _AIOSMTP_AVAILABLE:
            raise RuntimeError("aiosmtplib not installed. Run: pip install codex-platform[notifications]")
        await self._send_smtp(to, subject, html_content, text_content, headers, timeout)
        log.info("AsyncEmailClient | sent to='%s'", to)
        return True

    async def _send_smtp(
        self,
        to: str,
        subject: str,
        html_content: str | None,
        text_content: str | None,
        headers: ThreadHeadersDTO | None,
        timeout: int,
    ) -> None:
        message = EmailMessage()
        message["From"] = (
            formataddr((self.smtp_from_name, self.smtp_from_email))
            if self.smtp_from_name and self.smtp_from_email
            else self.smtp_from_email
        )
        message["To"] = to
        message["Subject"] = subject

        if headers is not None:
            for name, value in render_email_headers(headers).items():
                message[name] = value

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


__all__ = ["AsyncEmailClient", "_AIOSMTP_AVAILABLE", "aiosmtplib"]
