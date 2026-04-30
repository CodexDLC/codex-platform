"""Tests for codex_platform.streams.runtime."""

import asyncio

import pytest

from codex_platform.streams import StreamRouter, StreamRuntime, StreamRuntimeConfig

pytestmark = pytest.mark.unit


def test_partial_runtime_requires_non_monolith_group():
    config = StreamRuntimeConfig(
        stream_name="test:stream",
        consumer_group="monolith",
        consumer_name="worker-1",
        enabled_groups={"actor_state"},
    )

    with pytest.raises(ValueError, match="non-monolith"):
        StreamRuntime(object(), config)  # type: ignore[arg-type]


async def test_runtime_filters_handlers_by_enabled_groups(redis_client):
    router = StreamRouter()

    @router.on("actor.event", group="actor_state")
    async def actor_handler(payload: dict) -> None: ...

    @router.on("scenario.event", group="scenario")
    async def scenario_handler(payload: dict) -> None: ...

    config = StreamRuntimeConfig(
        stream_name="test:stream",
        consumer_group="actor_state_service",
        consumer_name="worker-1",
        enabled_groups={"actor_state"},
    )
    runtime = StreamRuntime(redis_client, config)

    runtime.include_router(router)

    assert set(runtime.dispatcher._handlers) == {"actor.event"}
    assert runtime.dispatcher._handlers["actor.event"][0].handler is actor_handler


async def test_runtime_monolith_processes_all_groups(redis_client):
    router = StreamRouter()
    received = []

    @router.on("actor.event", group="actor_state")
    async def actor_handler(payload: dict) -> None:
        received.append(("actor", payload["value"]))

    @router.on("scenario.event", group="scenario")
    async def scenario_handler(payload: dict) -> None:
        received.append(("scenario", payload["value"]))

    runtime = StreamRuntime(
        redis_client,
        StreamRuntimeConfig(
            stream_name="test:stream",
            consumer_group="monolith",
            consumer_name="worker-1",
            enabled_groups=None,
            poll_interval=0.01,
        ),
    )
    runtime.include_router(router)

    await runtime.producer.publish("actor.event", {"value": 1})
    await runtime.producer.publish("scenario.event", {"value": 2})
    await runtime.start()
    await asyncio.sleep(0.1)
    await runtime.stop()

    assert received == [("actor", 1), ("scenario", 2)]
