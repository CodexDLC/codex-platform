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

Typical setup::

    from codex_platform.streams import (
        StreamConsumer, StreamProducer,
        StreamProcessor, StreamRouter, StreamDispatcher,
    )

    # Producer
    producer = StreamProducer(redis_client, stream_name="events:orders")

    # Consumer + Processor
    consumer = StreamConsumer(redis_client, "events:orders", "workers", "worker_1")
    dispatcher = StreamDispatcher()

    @dispatcher.on("order.paid")
    async def handle_order(payload: dict) -> None:
        ...

    processor = StreamProcessor(
        storage=consumer,
        stream_name="events:orders",
        consumer_group_name="workers",
        consumer_name="worker_1",
    )
    processor.set_callback(dispatcher.process)
    await processor.start()
"""

from .consumer import StreamConsumer, StreamEvent
from .dispatcher import RetrySchedulerProtocol, StreamDispatcher
from .processor import StreamProcessor, StreamStorageProtocol
from .producer import StreamProducer
from .router import StreamRouter

__all__ = [
    "StreamProducer",
    "StreamConsumer",
    "StreamEvent",
    "StreamProcessor",
    "StreamStorageProtocol",
    "StreamRouter",
    "StreamDispatcher",
    "RetrySchedulerProtocol",
]
