"""
codex_platform.streams
=============================
Redis Streams broker — event sourcing / pub-sub layer.

Separate module from redis_service.
Streams are a message broker, not a data structure.

Components:
- ``StreamProducer``   — XADD (publish events)
- ``StreamConsumer``   — XREADGROUP + XACK (low-level read)
- ``StreamProcessor``  — background polling engine (wraps StreamConsumer)
- ``StreamRouter``     — groups handlers by event type (per-feature)
- ``StreamDispatcher`` — routes messages to handlers (generic, no DI)
- ``StreamRuntime``    — wires producer/consumer/dispatcher/processor with logical groups

Typical setup::

    from codex_platform.streams import (
        StreamConsumer, StreamProducer,
        StreamProcessor, StreamRouter, StreamDispatcher,
    )

    runtime = StreamRuntime(
        redis_client,
        StreamRuntimeConfig("events:orders", "monolith", "worker_1"),
    )

    router = StreamRouter()

    @router.on("order.paid", group="orders")
    async def handle_order(payload: dict) -> None:
        ...

    runtime.include_router(router)
    await runtime.start()
"""

from .consumer import StreamConsumer, StreamEvent
from .dispatcher import RetrySchedulerProtocol, StreamDispatcher
from .processor import StreamProcessor, StreamStorageProtocol
from .producer import StreamProducer, StreamReplyTimeoutError
from .router import StreamHandlerSpec, StreamRouter
from .runtime import StreamRuntime, StreamRuntimeConfig

__all__ = [
    "StreamProducer",
    "StreamReplyTimeoutError",
    "StreamConsumer",
    "StreamEvent",
    "StreamProcessor",
    "StreamStorageProtocol",
    "StreamRouter",
    "StreamHandlerSpec",
    "StreamDispatcher",
    "RetrySchedulerProtocol",
    "StreamRuntime",
    "StreamRuntimeConfig",
]
