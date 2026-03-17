"""
codex_platform.streams.processor
========================================
Redis Stream processing engine — continuous polling with consumer group.

Implements at-least-once delivery via XACK. Generic: works with any project,
not tied to any framework (bot, Django, FastAPI, etc.).

Usage::

    from codex_platform.streams import StreamConsumer
    from codex_platform.streams.processor import StreamProcessor, StreamStorageProtocol

    # Option 1: Use StreamConsumer directly (implements StreamStorageProtocol)
    consumer = StreamConsumer(redis_client, "events:bot", "bot_group", "worker_1")
    processor = StreamProcessor(storage=consumer, ...)

    # Option 2: Implement StreamStorageProtocol yourself (e.g. for testing)
    class FakeStorage:
        async def create_group(self, stream, group): ...
        async def read_events(self, stream, group, consumer, count): return []
        async def ack_event(self, stream, group, message_id): ...
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
from collections.abc import Awaitable, Callable
from typing import Any, Protocol, runtime_checkable

log = logging.getLogger(__name__)

MessageCallback = Callable[[dict[str, Any]], Awaitable[None]]


@runtime_checkable
class StreamStorageProtocol(Protocol):
    """Adapter protocol for Redis Stream I/O.

    ``StreamConsumer`` from ``streams.consumer`` implements this protocol.
    You can also implement it yourself for testing or alternative backends.
    """

    async def create_group(self, stream_name: str, group_name: str) -> None:
        """Creates a consumer group idempotently (XGROUP CREATE ... MKSTREAM)."""
        ...

    async def read_events(
        self,
        stream_name: str,
        group_name: str,
        consumer_name: str,
        count: int,
    ) -> list[tuple[str, dict[str, Any]]]:
        """Reads undelivered messages for the group (XREADGROUP ... >).

        Returns:
            List of (message_id, data_dict). Empty if no messages.
        """
        ...

    async def ack_event(self, stream_name: str, group_name: str, message_id: str) -> None:
        """Acknowledges message processing (XACK)."""
        ...


class StreamProcessor:
    """Async engine for consuming and dispatching Redis Stream events.

    Runs a continuous background polling loop. On each iteration reads a batch
    of messages from the consumer group, dispatches each to the registered
    callback, and ACKs on success.

    If the callback fails — message stays in PEL (unacknowledged) for future
    recovery. The processor recovers automatically if the consumer group is lost
    (NOGROUP error).

    Args:
        storage:             Any object implementing ``StreamStorageProtocol``.
                             Use ``StreamConsumer`` from streams.consumer.
        stream_name:         Redis Stream identifier.
        consumer_group_name: Shared group name (same across all instances = load balancing).
        consumer_name:       Unique name for this processor instance.
        batch_count:         Max messages per poll cycle.
        poll_interval:       Sleep duration (seconds) when no messages available.

    TODO:
        PEL recovery on startup — XPENDING/XCLAIM for messages stuck in PEL
        after a processor crash.

    Example::

        consumer = StreamConsumer(redis, "events:bot", "bot_group", "worker_1")
        processor = StreamProcessor(
            storage=consumer,
            stream_name="events:bot",
            consumer_group_name="bot_group",
            consumer_name="worker_1",
        )
        processor.set_callback(my_async_handler)
        await processor.start()
        # ... later
        await processor.stop()
    """

    def __init__(
        self,
        storage: StreamStorageProtocol,
        stream_name: str,
        consumer_group_name: str,
        consumer_name: str,
        batch_count: int = 10,
        poll_interval: float = 1.0,
    ) -> None:
        self.storage = storage
        self.stream_name = stream_name
        self.group_name = consumer_group_name
        self.consumer_name = consumer_name
        self.batch_count = batch_count
        self.poll_interval = poll_interval

        self.is_running = False
        self._callback: MessageCallback | None = None
        self._task: asyncio.Task[None] | None = None

    def set_callback(self, callback: MessageCallback) -> None:
        """Registers the message handler.

        Args:
            callback: ``async def handler(payload: dict) -> None``
        """
        self._callback = callback

    async def start(self) -> None:
        """Starts the background polling loop.

        Creates the consumer group (up to 5 attempts with 3s delay),
        then spawns ``_consume_loop`` as an asyncio Task.
        """
        if self.is_running:
            log.warning("StreamProcessor | already running stream='%s'", self.stream_name)
            return

        for attempt in range(1, 6):
            try:
                await self.storage.create_group(self.stream_name, self.group_name)
                break
            except Exception as e:
                log.warning("StreamProcessor | create_group attempt %d/5: %s", attempt, e)
                if attempt < 5:
                    await asyncio.sleep(3)
                else:
                    log.error("StreamProcessor | failed to create group, giving up")
                    return

        self.is_running = True
        self._task = asyncio.create_task(self._consume_loop())
        log.info(
            "StreamProcessor | started stream='%s' group='%s' consumer='%s'",
            self.stream_name,
            self.group_name,
            self.consumer_name,
        )

    async def stop(self) -> None:
        """Stops the polling loop gracefully."""
        self.is_running = False
        if self._task and not self._task.done():
            self._task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._task
        log.info("StreamProcessor | stopped stream='%s'", self.stream_name)

    async def _consume_loop(self) -> None:
        try:
            while self.is_running:
                try:
                    messages = await self.storage.read_events(
                        stream_name=self.stream_name,
                        group_name=self.group_name,
                        consumer_name=self.consumer_name,
                        count=self.batch_count,
                    )

                    if not messages:
                        await asyncio.sleep(self.poll_interval)
                        continue

                    for message_id, data in messages:
                        await self._process_one(message_id, data)

                except asyncio.CancelledError:
                    raise
                except Exception as e:
                    log.error("StreamProcessor | consume loop error: %s", e)
                    if "NOGROUP" in str(e):
                        log.warning("StreamProcessor | consumer group lost, recreating...")
                        with contextlib.suppress(Exception):
                            await self.storage.create_group(self.stream_name, self.group_name)
                    await asyncio.sleep(5)

        except asyncio.CancelledError:
            log.info("StreamProcessor | consume loop cancelled")
            raise

    async def _process_one(self, message_id: str, data: dict[str, Any]) -> None:
        """Processes a single message. ACKs on success, leaves in PEL on failure."""
        try:
            if self._callback:
                await self._callback(data)
            await self.storage.ack_event(self.stream_name, self.group_name, message_id)
            log.debug("StreamProcessor | ack id='%s'", message_id)
        except Exception as e:
            log.error("StreamProcessor | failed to process message id='%s': %s", message_id, e)
            # Message stays in PEL (unacknowledged) for recovery
