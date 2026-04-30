"""Tests for codex_platform.streams.dispatcher.StreamDispatcher."""

import pytest

from codex_platform.streams import StreamDispatcher, StreamRouter

pytestmark = pytest.mark.unit


class TestStreamDispatcherOn:
    """@dispatcher.on() direct handler registration."""

    def test_registers_handler(self):
        dispatcher = StreamDispatcher()

        @dispatcher.on("order.paid")
        async def handler(payload: dict) -> None: ...

        assert "order.paid" in dispatcher._handlers
        assert dispatcher._handlers["order.paid"][0].handler is handler


class TestIncludeRouter:
    """include_router() merges handlers from a StreamRouter."""

    def test_merges_handlers(self):
        router = StreamRouter()

        @router.on("booking.confirmed")
        async def h1(p): ...

        dispatcher = StreamDispatcher()
        dispatcher.include_router(router)

        assert "booking.confirmed" in dispatcher._handlers
        assert dispatcher._handlers["booking.confirmed"][0].handler is h1

    def test_merges_multiple_routers(self):
        r1 = StreamRouter()
        r2 = StreamRouter()

        @r1.on("a")
        async def ha(p): ...

        @r2.on("b")
        async def hb(p): ...

        dispatcher = StreamDispatcher()
        dispatcher.include_router(r1)
        dispatcher.include_router(r2)

        assert "a" in dispatcher._handlers
        assert "b" in dispatcher._handlers

    def test_merges_same_event_type(self):
        r1 = StreamRouter()
        r2 = StreamRouter()

        @r1.on("x")
        async def h1(p): ...

        @r2.on("x")
        async def h2(p): ...

        dispatcher = StreamDispatcher()
        dispatcher.include_router(r1)
        dispatcher.include_router(r2)

        assert len(dispatcher._handlers["x"]) == 2

    def test_filters_router_by_enabled_groups(self):
        router = StreamRouter()

        @router.on("a", group="actor_state")
        async def actor_handler(p): ...

        @router.on("b", group="scenario")
        async def scenario_handler(p): ...

        @router.on("c")
        async def shared_handler(p): ...

        dispatcher = StreamDispatcher()
        dispatcher.include_router(router, enabled_groups={"actor_state"})

        assert set(dispatcher._handlers) == {"a", "c"}
        assert dispatcher._handlers["a"][0].handler is actor_handler
        assert dispatcher._handlers["c"][0].handler is shared_handler


class TestProcess:
    """dispatcher.process() dispatching logic."""

    async def test_dispatches_to_matching_handler(self):
        dispatcher = StreamDispatcher()
        calls = []

        @dispatcher.on("order.paid")
        async def handler(payload: dict) -> None:
            calls.append(payload)

        await dispatcher.process({"type": "order.paid", "amount": "100"})
        assert len(calls) == 1
        assert calls[0]["amount"] == "100"

    async def test_no_matching_handlers_no_error(self):
        dispatcher = StreamDispatcher()
        # Should not raise
        await dispatcher.process({"type": "unknown.event"})

    async def test_missing_type_field_returns(self):
        dispatcher = StreamDispatcher()
        calls = []

        @dispatcher.on("anything")
        async def handler(payload: dict) -> None:
            calls.append(payload)

        await dispatcher.process({"data": "no type field"})
        assert calls == []

    async def test_filter_func_true_calls_handler(self):
        dispatcher = StreamDispatcher()
        calls = []

        @dispatcher.on("alert", filter_func=lambda p: p.get("urgent") == "yes")
        async def handler(payload: dict) -> None:
            calls.append(payload)

        await dispatcher.process({"type": "alert", "urgent": "yes"})
        assert len(calls) == 1

    async def test_filter_func_false_skips_handler(self):
        dispatcher = StreamDispatcher()
        calls = []

        @dispatcher.on("alert", filter_func=lambda p: p.get("urgent") == "yes")
        async def handler(payload: dict) -> None:
            calls.append(payload)

        await dispatcher.process({"type": "alert", "urgent": "no"})
        assert calls == []

    async def test_handler_failure_with_retry_scheduler(self):
        retries = []

        class FakeRetryScheduler:
            async def schedule_retry(self, stream_name, payload, delay=60):
                retries.append((stream_name, payload, delay))

        dispatcher = StreamDispatcher(retry_scheduler=FakeRetryScheduler())

        @dispatcher.on("fail")
        async def handler(payload: dict) -> None:
            raise ValueError("boom")

        # Should not raise because retry_scheduler is set
        await dispatcher.process({"type": "fail"}, stream_name="test:stream")
        assert len(retries) == 1
        assert retries[0][0] == "test:stream"

    async def test_handler_failure_without_retry_scheduler_reraises(self):
        dispatcher = StreamDispatcher()

        @dispatcher.on("fail")
        async def handler(payload: dict) -> None:
            raise ValueError("boom")

        with pytest.raises(ValueError, match="boom"):
            await dispatcher.process({"type": "fail"})
