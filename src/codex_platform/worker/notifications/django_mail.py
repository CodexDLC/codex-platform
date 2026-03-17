"""
codex_platform.worker.notifications.django_mail
==============================================
Django mail delivery channel — implements ``DeliveryChannel``.

Wraps ``django.core.mail.send_mail`` in ``asyncio.to_thread`` so it
can be safely called from inside an async orchestrator without blocking
the event loop.

Note: This channel requires Django to be installed and fully configured
(``DJANGO_SETTINGS_MODULE`` set, ``EMAIL_HOST`` defined in settings).

Requires: pip install codex-tools[django]
"""

import asyncio
import logging

log = logging.getLogger(__name__)


class DjangoMailChannel:
    """
    Async-safe Django email channel. Implements ``DeliveryChannel``.

    Uses ``asyncio.to_thread`` to run Django's synchronous ``send_mail``
    without blocking the async event loop.

    Usage:
        channel = DjangoMailChannel(from_email="noreply@example.com")
        success = await channel.send(
            to="user@example.com",
            subject="Hello",
            html_content="<b>Hi</b>",
            text_content="Hi",
        )
    """

    def __init__(self, from_email: str | None = None) -> None:
        """
        Args:
            from_email: Sender address. If None, Django's ``DEFAULT_FROM_EMAIL``
                        setting is used.
        """
        self.from_email = from_email

    def is_available(self) -> bool:
        """
        Returns True if Django email is configured (EMAIL_HOST is set in settings).
        Safe to call without a running event loop.
        """
        try:
            from django.conf import settings  # lazy import

            host = getattr(settings, "EMAIL_HOST", "")
            return bool(host and host != "localhost")
        except Exception:
            return False

    async def send(
        self,
        to: str,
        subject: str,
        html_content: str | None,
        text_content: str | None,
    ) -> bool:
        """
        Send email via Django's mail backend, non-blocking.

        Args:
            to: Recipient email address.
            subject: Email subject line.
            html_content: HTML body. Used as ``html_message`` in ``send_mail``.
            text_content: Plain-text body. Used as ``message`` in ``send_mail``.
                          Falls back to stripped HTML or generic text if None.

        Returns:
            True on success.

        Raises:
            django.core.mail.BadHeaderError: If subject or addresses contain newlines.
            smtplib.SMTPException: On SMTP transport failure.
            RuntimeError: If Django is not configured.
        """
        from django.core.mail import send_mail  # lazy import
        from django.utils.html import strip_tags  # lazy import

        plain = text_content or (strip_tags(html_content) if html_content else "")

        log.debug("DjangoMailChannel | sending to='%s' subject='%s'", to, subject)

        await asyncio.to_thread(
            send_mail,
            subject=subject,
            message=plain,
            from_email=self.from_email,  # None → DEFAULT_FROM_EMAIL
            recipient_list=[to],
            html_message=html_content,
            fail_silently=False,
        )

        log.info("DjangoMailChannel | sent to='%s'", to)
        return True
