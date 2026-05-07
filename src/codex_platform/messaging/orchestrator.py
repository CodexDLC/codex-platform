"""Fallback delivery orchestrator."""

from __future__ import annotations

import logging
from inspect import Parameter, signature
from typing import Protocol, runtime_checkable

from .dto import NotificationPayloadDTO, ThreadHeadersDTO

log = logging.getLogger(__name__)


@runtime_checkable
class DeliveryChannel(Protocol):
    """Contract for a single delivery method."""

    async def send(
        self,
        to: str,
        subject: str,
        html_content: str | None,
        text_content: str | None,
        headers: ThreadHeadersDTO | None = None,
    ) -> bool:
        """Attempt delivery. Return True on success, False on logical failure."""
        ...

    def is_available(self) -> bool:
        """Return True if this channel is properly configured and ready."""
        ...


class BaseDeliveryOrchestrator:
    """Tries channels in order and stops on the first successful delivery."""

    def __init__(self, channels: list[DeliveryChannel]) -> None:
        self.channels = channels

    async def deliver(self, payload: NotificationPayloadDTO) -> bool:
        """Deliver a notification payload through available channels."""

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
                html_content = getattr(payload, "html_content", None)
                text_content = getattr(payload, "text_content", None)
                headers = getattr(payload, "headers", None)
                send_parameters = signature(channel.send).parameters
                supports_headers = "headers" in send_parameters or any(
                    parameter.kind == Parameter.VAR_KEYWORD for parameter in send_parameters.values()
                )
                delivered = (
                    await channel.send(
                        to=to,
                        subject=subject,
                        html_content=html_content,
                        text_content=text_content,
                        headers=headers,
                    )
                    if supports_headers
                    else await channel.send(
                        to=to,
                        subject=subject,
                        html_content=html_content,
                        text_content=text_content,
                    )
                )

                if delivered:
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


__all__ = ["DeliveryChannel", "BaseDeliveryOrchestrator"]
