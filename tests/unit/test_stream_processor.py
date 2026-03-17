"""Tests for codex_platform.streams.processor.StreamProcessor."""

import asyncio
from typing import Any

import pytest

from codex_platform.streams.processor import StreamProcessor

pytestmark = pytest.mark.unit


class FakeStorage:
    """In-memory implementation of StreamStorageProtocol for testing."""

    def __init__(
        self,
        messages: list[tuple[str, dict[str, Any]]] | None = None,
        create_group_error: Exception | None = None,
    ) -> None:
        self._messages = list(messages or [])
        self._delivered = False
        self._create_group_error = create_group_error
        self.created_groups: list[tuple[str, str]] = []
        self.acked: list[tuple[str, str, str]] = []

    async def create_group(self, stream_name: str, group_name: str) -> None:
        if self._create_group_error:
            raise self._create_group_error
        self.created_groups.append((stream_name, group_name))

    async def read_events(
        self,
        stream_name: str,
        group_name: str,
        consumer_name: str,
        count: int,
    ) -> list[tuple[str, dict[str, Any]]]:
        if not self._delivered and self._messages:
            self._delivered = True
            return self._messages
        return []

    async def ack_event(self, stream_name: str, group_name: str, message_id: str) -> None:
        self.acked.append((stream_name, group_name, message_id))


class TestStreamProcessorStartStop:
    """start() and stop() lifecycle."""

    async def test_start_creates_group_and_runs(self):
        storage = FakeStorage()
        proc = StreamProcessor(
            storage=storage,
            stream_name="s",
            consumer_group_name="g",
            consumer_name="c",
            poll_interval=0.01,
        )
        proc.set_callback(lambda data: asyncio.sleep(0))

        await proc.start()
        assert proc.is_running is True
        assert storage.created_groups == [("s", "g")]

        await proc.stop()
        assert proc.is_running is False

    async def test_stop_cancels_loop(self):
        storage = FakeStorage()
        proc = StreamProcessor(
            storage=storage,
            stream_name="s",
            consumer_group_name="g",
            consumer_name="c",
            poll_interval=0.01,
        )
        proc.set_callback(lambda data: asyncio.sleep(0))

        await proc.start()
        task = proc._task
        await proc.stop()

        assert task is not None
        assert task.done()

    async def test_start_twice_does_not_duplicate(self):
        storage = FakeStorage()
        proc = StreamProcessor(
            storage=storage,
            stream_name="s",
            consumer_group_name="g",
            consumer_name="c",
            poll_interval=0.01,
        )
        proc.set_callback(lambda data: asyncio.sleep(0))

        await proc.start()
        task1 = proc._task
        await proc.start()  # second call — should be ignored
        task2 = proc._task

        assert task1 is task2
        await proc.stop()


class TestStreamProcessorDispatch:
    """Messages dispatched to callback, ACK on success."""

    async def test_messages_dispatched_to_callback(self):
        messages = [("1-0", {"type": "ping", "value": "42"})]
        storage = FakeStorage(messages=messages)
        received = []

        async def callback(data):
            received.append(data)

        proc = StreamProcessor(
            storage=storage,
            stream_name="s",
            consumer_group_name="g",
            consumer_name="c",
            poll_interval=0.01,
        )
        proc.set_callback(callback)

        await proc.start()
        await asyncio.sleep(0.1)
        await proc.stop()

        assert len(received) == 1
        assert received[0] == {"type": "ping", "value": "42"}

    async def test_ack_on_success(self):
        messages = [("1-0", {"type": "ok"})]
        storage = FakeStorage(messages=messages)

        async def callback(data):
            pass

        proc = StreamProcessor(
            storage=storage,
            stream_name="s",
            consumer_group_name="g",
            consumer_name="c",
            poll_interval=0.01,
        )
        proc.set_callback(callback)

        await proc.start()
        await asyncio.sleep(0.1)
        await proc.stop()

        assert ("s", "g", "1-0") in storage.acked

    async def test_no_ack_on_callback_failure(self):
        messages = [("1-0", {"type": "fail"})]
        storage = FakeStorage(messages=messages)

        async def callback(data):
            raise RuntimeError("handler error")

        proc = StreamProcessor(
            storage=storage,
            stream_name="s",
            consumer_group_name="g",
            consumer_name="c",
            poll_interval=0.01,
        )
        proc.set_callback(callback)

        await proc.start()
        await asyncio.sleep(0.1)
        await proc.stop()

        # Message should NOT have been ACKed
        assert ("s", "g", "1-0") not in storage.acked
