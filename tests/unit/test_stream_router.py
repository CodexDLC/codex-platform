"""Tests for codex_platform.streams.router.StreamRouter."""

import pytest

from codex_platform.streams import StreamRouter

pytestmark = pytest.mark.unit


class TestStreamRouterOn:
    """@router.on() decorator registration."""

    def test_registers_handler(self):
        router = StreamRouter()

        @router.on("order.paid")
        async def handler(payload: dict) -> None: ...

        assert "order.paid" in router.handlers
        assert len(router.handlers["order.paid"]) == 1
        assert router.handlers["order.paid"][0].handler is handler

    def test_multiple_handlers_for_same_event(self):
        router = StreamRouter()

        @router.on("order.paid")
        async def handler_a(payload: dict) -> None: ...

        @router.on("order.paid")
        async def handler_b(payload: dict) -> None: ...

        assert len(router.handlers["order.paid"]) == 2
        assert router.handlers["order.paid"][0].handler is handler_a
        assert router.handlers["order.paid"][1].handler is handler_b

    def test_filter_func_stored(self):
        router = StreamRouter()

        def my_filter(p):
            return p.get("urgent", False)

        @router.on("alert.created", filter_func=my_filter)
        async def handler(payload: dict) -> None: ...

        spec = router.handlers["alert.created"][0]
        assert spec.filter_func is my_filter

    def test_filter_func_none_by_default(self):
        router = StreamRouter()

        @router.on("ping")
        async def handler(payload: dict) -> None: ...

        spec = router.handlers["ping"][0]
        assert spec.filter_func is None

    def test_group_and_reply_stored(self):
        router = StreamRouter()

        @router.on("actor_state.snapshots_requested", group="actor_state", reply=True)
        async def handler(payload: dict) -> None: ...

        spec = router.handlers["actor_state.snapshots_requested"][0]
        assert spec.group == "actor_state"
        assert spec.reply is True
        assert spec.event_type == "actor_state.snapshots_requested"


class TestStreamRouterHandlers:
    """handlers property."""

    def test_returns_dict(self):
        router = StreamRouter()
        assert isinstance(router.handlers, dict)

    def test_empty_by_default(self):
        router = StreamRouter()
        assert router.handlers == {}

    def test_returns_registered_event_types(self):
        router = StreamRouter()

        @router.on("a")
        async def h1(p): ...

        @router.on("b")
        async def h2(p): ...

        assert set(router.handlers.keys()) == {"a", "b"}

    def test_decorator_returns_original_function(self):
        router = StreamRouter()

        async def original(payload: dict) -> None: ...

        decorated = router.on("test")(original)
        assert decorated is original
