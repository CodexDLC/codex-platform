"""
codex_platform.streams.runtime
==============================
Runtime wiring for Redis Streams processors, routers, and logical groups.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from redis.asyncio import Redis

from .consumer import StreamConsumer
from .dispatcher import RetrySchedulerProtocol, StreamDispatcher
from .processor import StreamProcessor
from .producer import StreamProducer
from .router import StreamRouter


@dataclass(frozen=True)
class StreamRuntimeConfig:
    """Configuration for one running Redis Streams worker process."""

    stream_name: str
    consumer_group: str
    consumer_name: str
    enabled_groups: Iterable[str] | None = None
    batch_count: int = 10
    poll_interval: float = 1.0
    block_ms: int | None = 1000
    default_monolith_group: str = "monolith"

    @property
    def enabled_group_set(self) -> set[str] | None:
        """Normalized logical groups, or ``None`` when all handlers are enabled."""
        return None if self.enabled_groups is None else set(self.enabled_groups)

    def validate(self) -> None:
        """Reject ambiguous partial-group startup on the default monolith group."""
        if self.enabled_group_set is not None and self.consumer_group == self.default_monolith_group:
            raise ValueError("Partial stream runtimes must use an explicit non-monolith consumer_group")


class StreamRuntime:
    """Convenience runtime for grouped Redis Streams handlers.

    A runtime owns a dispatcher, consumer, producer, and processor for one Redis
    stream. Logical handler groups are selected by ``StreamRuntimeConfig`` while
    Redis delivery remains controlled by ``consumer_group``.
    """

    def __init__(
        self,
        redis: Redis,
        config: StreamRuntimeConfig,
        *,
        retry_scheduler: RetrySchedulerProtocol | None = None,
    ) -> None:
        config.validate()
        self.redis = redis
        self.config = config
        self.dispatcher = StreamDispatcher(retry_scheduler=retry_scheduler)
        self.producer = StreamProducer(redis, config.stream_name)
        self.consumer = StreamConsumer(
            redis,
            config.stream_name,
            config.consumer_group,
            config.consumer_name,
        )
        self.processor = StreamProcessor(
            storage=self.consumer,
            stream_name=config.stream_name,
            consumer_group_name=config.consumer_group,
            consumer_name=config.consumer_name,
            batch_count=config.batch_count,
            poll_interval=config.poll_interval,
            block_ms=config.block_ms,
        )
        self.processor.set_callback(self.dispatcher.process)

    def include_router(self, router: StreamRouter) -> None:
        """Include handlers from a router, respecting configured logical groups."""
        self.dispatcher.include_router(router, enabled_groups=self.config.enabled_group_set)

    async def start(self) -> None:
        """Start the underlying stream processor."""
        await self.processor.start()

    async def stop(self) -> None:
        """Stop the underlying stream processor."""
        await self.processor.stop()
