"""
codex_platform.worker.notifications.orchestrator
===============================================
Fallback delivery orchestrator.
Tries channels in order; stops on first success.

Usage:
    registry = ChannelRegistry()
    registry.register("smtp", lambda cfg: AsyncEmailClient(...))
    channels = registry.build_channels(settings)

    orchestrator = BaseDeliveryOrchestrator(channels=channels)
    success = await orchestrator.deliver(payload_dto)
"""

import logging
from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from codex_platform.notifications.dto import NotificationPayloadDTO

log = logging.getLogger(__name__)


@runtime_checkable
class DeliveryChannel(Protocol):
    """
    Contract for a single delivery method.

    Implementors: AsyncEmailClient, DjangoMailChannel, TelegramChannel, etc.
    """

    async def send(
        self,
        to: str,
        subject: str,
        html_content: str | None,
        text_content: str | None,
    ) -> bool:
        """
        Attempt delivery. Return True on success, False on logical failure.
        Raise on infrastructure errors (so the orchestrator can log and try next channel).
        """
        ...

    def is_available(self) -> bool:
        """Return True if this channel is properly configured and ready."""
        ...


class BaseDeliveryOrchestrator:
    """
    Tries channels in order; stops on first success.

    Channels are injected at construction time via Dependency Injection.
    ``deliver()`` is a pure send operation with no side effects beyond delivery.
    """

    def __init__(self, channels: list[DeliveryChannel]) -> None:
        """
        Args:
            channels: Ordered list of delivery channels to try.
                      Use ``ChannelRegistry.build_channels()`` to build this list.
        """
        self.channels = channels

    async def deliver(self, payload: "NotificationPayloadDTO") -> bool:
        """
        Deliver a notification payload through available channels.

        Tries each channel in order; stops on first success.
        If a channel raises, logs the exception and falls through to the next.

        Args:
            payload: ``NotificationPayloadDTO`` with ready-made html/text content.

        Returns:
            True if at least one channel succeeded, False if all exhausted.
        """
        to = payload.recipient.email or payload.recipient.phone or ""
        subject = payload.subject or ""

        if not to:
            log.error(
                "DeliveryOrchestrator | no recipient address, notification_id=%s",
                payload.notification_id,
            )
            return False

        for channel in self.channels:
            if not channel.is_available():
                continue
            try:
                if await channel.send(
                    to=to,
                    subject=subject,
                    html_content=payload.html_content,
                    text_content=payload.text_content,
                ):
                    log.info(
                        "DeliveryOrchestrator | delivered via %s, notification_id=%s",
                        type(channel).__name__,
                        payload.notification_id,
                    )
                    return True
            except Exception:
                log.exception(
                    "DeliveryOrchestrator | channel=%s failed, trying next",
                    type(channel).__name__,
                )

        log.error(
            "DeliveryOrchestrator | all channels exhausted, notification_id=%s",
            payload.notification_id,
        )
        return False
