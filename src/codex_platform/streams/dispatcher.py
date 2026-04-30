"""
codex_platform.streams.dispatcher
==========================================
Generic Stream event dispatcher — routes messages to registered handlers.

Framework-agnostic: no DI container, no bot references.
For framework-specific dispatchers (e.g. with a DI container) — extend this class.

Usage::

    from codex_platform.streams.dispatcher import StreamDispatcher
    from codex_platform.streams.router import StreamRouter

    dispatcher = StreamDispatcher()

    # Register handlers directly:
    @dispatcher.on("booking.confirmed")
    async def handle_booking(payload: dict) -> None:
        ...

    # Or include a router from a feature module:
    dispatcher.include_router(notifications_router)

    # Connect to StreamProcessor:
    processor.set_callback(dispatcher.process)
    await processor.start()

Extending for framework-specific DI::

    class BotDispatcher(StreamDispatcher):
        def __init__(self, container):
            super().__init__()
            self.container = container

        async def process(self, payload: dict) -> None:
            # inject container into handlers, etc.
            ...
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

if TYPE_CHECKING:
    from .router import FilterFunc, HandlerFunc, StreamHandlerSpec, StreamRouter

log = logging.getLogger(__name__)


@runtime_checkable
class RetrySchedulerProtocol(Protocol):
    """Protocol for a retry scheduler (ARQ, Celery, etc.).

    Pass to ``StreamDispatcher`` for automatic rescheduling of failed messages.
    """

    async def schedule_retry(
        self,
        stream_name: str,
        payload: dict[str, Any],
        delay: int = 60,
    ) -> None:
        """Schedules message reprocessing after a delay.

        Args:
            stream_name: Redis Stream name.
            payload:     Original message data.
            delay:       Retry delay in seconds.
        """
        ...


class StreamDispatcher:
    """Routes Redis Stream messages to registered handlers by event type.

    Handlers are registered via ``@dispatcher.on(event_type)`` decorator
    or by including ``StreamRouter`` instances.

    On handler failure: if a ``retry_scheduler`` is provided, the message
    is scheduled for retry. Otherwise the exception is re-raised (message
    stays in PEL, unacknowledged).

    Args:
        retry_scheduler: Optional retry scheduler implementing ``RetrySchedulerProtocol``.

    Example::

        dispatcher = StreamDispatcher()

        @dispatcher.on("user.registered")
        async def welcome(payload: dict) -> None:
            await send_welcome_email(payload["email"])

        processor.set_callback(dispatcher.process)
    """

    def __init__(self, retry_scheduler: RetrySchedulerProtocol | None = None) -> None:
        self._retry_scheduler = retry_scheduler
        self._handlers: dict[str, list[StreamHandlerSpec]] = {}
        log.info("StreamDispatcher | initialized")

    def include_router(self, router: StreamRouter, *, enabled_groups: set[str] | None = None) -> None:
        """Merges handlers from a ``StreamRouter`` into this dispatcher.

        Args:
            router: Router from a feature module.
            enabled_groups: Optional logical handler groups to include.
        """
        for event_type, handlers in router.handlers.items():
            selected = [
                spec
                for spec in handlers
                if enabled_groups is None or spec.group is None or spec.group in enabled_groups
            ]
            if selected:
                if event_type not in self._handlers:
                    self._handlers[event_type] = []
                self._handlers[event_type].extend(selected)
        log.info("StreamDispatcher | included router types=%s", list(router.handlers.keys()))

    def on(
        self,
        event_type: str,
        filter_func: FilterFunc | None = None,
        *,
        group: str | None = None,
        reply: bool = False,
    ) -> Callable[[HandlerFunc], HandlerFunc]:
        """Decorator for registering a handler directly on the dispatcher.

        Args:
            event_type:  Stream message type (e.g. ``"booking.confirmed"``).
            filter_func: Optional ``payload -> bool`` filter.
            group: Optional logical processing group used by ``StreamRuntime``.
            reply: Whether the handler participates in request/reply flows.
        """
        from .router import StreamHandlerSpec

        def decorator(handler: HandlerFunc) -> HandlerFunc:
            if event_type not in self._handlers:
                self._handlers[event_type] = []
            self._handlers[event_type].append(
                StreamHandlerSpec(
                    event_type=event_type,
                    handler=handler,
                    filter_func=filter_func,
                    group=group,
                    reply=reply,
                )
            )
            return handler

        return decorator

    async def process(self, payload: dict[str, Any], stream_name: str = "") -> None:
        """Dispatches an incoming message to matching handlers.

        Called by ``StreamProcessor`` on each incoming message.

        Args:
            payload:     Message data dict. Must contain ``"type"`` field.
            stream_name: Stream name (used for retry scheduling only).
        """
        event_type = payload.get("type")
        if not event_type:
            log.warning("StreamDispatcher | message without 'type' field: %s", payload)
            return

        handlers = self._handlers.get(event_type, [])
        if not handlers:
            log.debug("StreamDispatcher | no handlers for type='%s'", event_type)
            return

        for spec in handlers:
            try:
                if spec.filter_func is None or spec.filter_func(payload):
                    log.debug("StreamDispatcher | calling %s for type='%s'", spec.handler.__name__, event_type)
                    await spec.handler(payload)
            except Exception as e:
                log.error("StreamDispatcher | handler %s failed: %s", spec.handler.__name__, e)

                if self._retry_scheduler:
                    try:
                        await self._retry_scheduler.schedule_retry(
                            stream_name=stream_name,
                            payload=payload,
                            delay=60,
                        )
                        log.info("StreamDispatcher | retry scheduled for type='%s'", event_type)
                        return
                    except Exception as retry_err:
                        log.error("StreamDispatcher | retry scheduling failed: %s", retry_err)

                raise
