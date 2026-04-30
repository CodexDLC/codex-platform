"""
codex_platform.streams.router
=====================================
Stream event router — groups handlers by message type.

Analogous to Aiogram/FastAPI routers: define handlers in feature modules,
then include into a dispatcher. Framework-agnostic.

Usage::

    from codex_platform.streams.router import StreamRouter

    router = StreamRouter()

    @router.on("booking.confirmed")
    async def handle_booking(payload: dict) -> None:
        booking_id = payload["booking_id"]
        ...

    @router.on("notification.created", filter_func=lambda p: p.get("urgent"))
    async def handle_urgent(payload: dict) -> None:
        ...
"""

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

HandlerFunc = Callable[[dict[str, Any]], Any]
FilterFunc = Callable[[dict[str, Any]], bool]


@dataclass(frozen=True)
class StreamHandlerSpec:
    """Registered stream handler metadata."""

    event_type: str
    handler: HandlerFunc
    filter_func: FilterFunc | None = None
    group: str | None = None
    reply: bool = False


class StreamRouter:
    """Groups Redis Stream event handlers by message type.

    After populating, include into a ``StreamDispatcher`` via ``include_router()``.

    Example::

        router = StreamRouter()

        @router.on("order.paid")
        async def on_order_paid(payload: dict) -> None:
            ...

        dispatcher.include_router(router)
    """

    def __init__(self) -> None:
        self._handlers: dict[str, list[StreamHandlerSpec]] = {}

    def on(
        self,
        event_type: str,
        filter_func: FilterFunc | None = None,
        *,
        group: str | None = None,
        reply: bool = False,
    ) -> Callable[[HandlerFunc], HandlerFunc]:
        """Decorator for registering a handler for an event type.

        Args:
            event_type:  Stream message type (e.g. ``"booking.confirmed"``).
            filter_func: Optional ``payload -> bool`` filter. Handler is called
                         only when filter returns ``True``.
            group: Optional logical processing group used by ``StreamRuntime``.
            reply: Whether the handler participates in request/reply flows.

        Returns:
            Decorator (returns the original handler unchanged).
        """

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

    @property
    def handlers(self) -> dict[str, list[StreamHandlerSpec]]:
        """Registered handlers (read-only)."""
        return self._handlers
