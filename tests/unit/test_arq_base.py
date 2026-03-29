"""Tests for codex_platform.workers.arq.base."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from codex_platform.workers.arq.base import (
    CORE_FUNCTIONS,
    BaseArqService,
    BaseArqWorkerSettings,
    base_shutdown,
    base_startup,
    requeue_to_stream,
)

pytestmark = pytest.mark.unit


class FakePool:
    def __init__(self, job=None, *, enqueue_error: Exception | None = None, close_error: Exception | None = None):
        self.job = job
        self.enqueue_error = enqueue_error
        self.close_error = close_error
        self.closed = False
        self.calls: list[tuple[str, tuple, dict]] = []

    async def enqueue_job(self, function, *args, **kwargs):
        self.calls.append((function, args, kwargs))
        if self.enqueue_error:
            raise self.enqueue_error
        return self.job

    async def close(self):
        self.closed = True
        if self.close_error:
            raise self.close_error


class FakeStreamManager:
    def __init__(self):
        self.calls: list[tuple[str, dict[str, str]]] = []

    async def add_event(self, stream_name: str, payload: dict[str, str]) -> None:
        self.calls.append((stream_name, dict(payload)))


class TestBaseArqService:
    async def test_init_creates_pool(self, monkeypatch):
        fake_pool = FakePool()

        async def fake_create_pool(redis_settings):
            assert redis_settings == "settings"
            return fake_pool

        monkeypatch.setattr("codex_platform.workers.arq.base.create_pool", fake_create_pool)
        service = BaseArqService("settings")

        await service.init()

        assert service.pool is fake_pool

    async def test_init_is_noop_when_pool_exists(self, monkeypatch):
        async def unexpected(_):
            raise AssertionError("create_pool should not be called")

        service = BaseArqService("settings")
        service.pool = FakePool()
        monkeypatch.setattr("codex_platform.workers.arq.base.create_pool", unexpected)

        await service.init()

        assert service.pool is not None

    async def test_init_reraises_pool_errors(self, monkeypatch):
        async def failing_create_pool(_):
            raise RuntimeError("boom")

        monkeypatch.setattr("codex_platform.workers.arq.base.create_pool", failing_create_pool)
        service = BaseArqService("settings")

        with pytest.raises(RuntimeError, match="boom"):
            await service.init()

    async def test_close_closes_pool(self):
        pool = FakePool()
        service = BaseArqService("settings")
        service.pool = pool

        await service.close()

        assert pool.closed is True

    async def test_close_swallows_pool_errors(self):
        pool = FakePool(close_error=RuntimeError("close failed"))
        service = BaseArqService("settings")
        service.pool = pool

        await service.close()

        assert pool.closed is True

    async def test_enqueue_job_initializes_pool_on_first_use(self, monkeypatch):
        job = SimpleNamespace(job_id="job-1")
        pool = FakePool(job=job)

        async def fake_create_pool(_):
            return pool

        monkeypatch.setattr("codex_platform.workers.arq.base.create_pool", fake_create_pool)
        service = BaseArqService("settings")

        result = await service.enqueue_job("send_email", 1, user_id=2)

        assert result is job
        assert pool.calls == [("send_email", (1,), {"user_id": 2})]

    async def test_enqueue_job_returns_none_on_enqueue_error(self):
        pool = FakePool(enqueue_error=RuntimeError("queue down"))
        service = BaseArqService("settings")
        service.pool = pool

        result = await service.enqueue_job("send_email")

        assert result is None


class TestWorkerHooks:
    async def test_base_startup_creates_health_file(self, monkeypatch, tmp_path):
        health_file = tmp_path / "worker.health"
        monkeypatch.setattr("codex_platform.workers.arq.base.HEALTH_FILE", health_file)

        await base_startup({})

        assert health_file.exists()

    async def test_base_shutdown_removes_health_file(self, monkeypatch, tmp_path):
        health_file = tmp_path / "worker.health"
        health_file.write_text("ok", encoding="utf-8")
        monkeypatch.setattr("codex_platform.workers.arq.base.HEALTH_FILE", health_file)

        await base_shutdown({})

        assert not health_file.exists()


class TestRequeueToStream:
    async def test_returns_when_stream_manager_missing(self):
        await requeue_to_stream({}, "events", {"id": "1"})

    async def test_requeues_with_incremented_retry(self):
        manager = FakeStreamManager()
        payload = {"id": "1"}

        await requeue_to_stream({"stream_manager": manager}, "events", payload)

        assert manager.calls == [("events", {"id": "1", "_retries": "1"})]

    async def test_requeues_existing_retry_counter(self):
        manager = FakeStreamManager()
        payload = {"id": "1", "_retries": "2"}

        await requeue_to_stream({"stream_manager": manager}, "events", payload)

        assert manager.calls == [("events", {"id": "1", "_retries": "3"})]

    async def test_moves_to_dlq_after_retry_limit(self):
        manager = FakeStreamManager()
        payload = {"id": "1", "_retries": "5"}

        await requeue_to_stream({"stream_manager": manager}, "events", payload)

        stream_name, dlq_payload = manager.calls[0]
        assert stream_name == "events:dlq"
        assert dlq_payload["id"] == "1"
        assert dlq_payload["_original_stream"] == "events"
        assert "_failed_at" in dlq_payload


def test_base_worker_settings_defaults():
    assert BaseArqWorkerSettings.on_startup is base_startup
    assert BaseArqWorkerSettings.on_shutdown is base_shutdown
    assert BaseArqWorkerSettings.max_retries == 5
    assert [requeue_to_stream] == CORE_FUNCTIONS
