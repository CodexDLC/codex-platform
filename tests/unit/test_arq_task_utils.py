"""Tests for codex_platform.workers.arq.task_utils (arq_task decorator)."""

import pytest

try:
    from arq import Retry

    from codex_platform.workers.arq.task_utils import arq_task

    SKIP = False
except ImportError:
    SKIP = True

pytestmark = [pytest.mark.unit, pytest.mark.skipif(SKIP, reason="arq not installed")]


class TestArqTask:
    async def test_successful_execution_returns_result(self):
        @arq_task(max_retries=3)
        async def my_task(ctx, value):
            return value * 2

        result = await my_task({"job_try": 1}, 21)
        assert result == 42

    async def test_exception_before_max_retries_raises_retry(self):
        @arq_task(retry_backoff=10, max_retries=5)
        async def failing_task(ctx):
            raise ValueError("boom")

        with pytest.raises(Retry) as exc_info:
            await failing_task({"job_try": 2})

        # defer = job_try * retry_backoff = 2 * 10 = 20
        assert exc_info.value.defer == 20

    async def test_exception_at_max_retries_returns_none(self):
        @arq_task(retry_backoff=10, max_retries=3)
        async def failing_task(ctx):
            raise ValueError("boom")

        result = await failing_task({"job_try": 3})
        assert result is None

    async def test_exception_above_max_retries_returns_none(self):
        @arq_task(retry_backoff=10, max_retries=3)
        async def failing_task(ctx):
            raise ValueError("boom")

        result = await failing_task({"job_try": 5})
        assert result is None

    async def test_retry_exception_is_reraised(self):
        @arq_task(max_retries=5)
        async def retry_task(ctx):
            raise Retry(defer=99)

        with pytest.raises(Retry) as exc_info:
            await retry_task({"job_try": 1})

        assert exc_info.value.defer == 99

    async def test_default_job_try_is_one(self):
        @arq_task(retry_backoff=10, max_retries=5)
        async def failing_task(ctx):
            raise ValueError("boom")

        # ctx without job_try key → defaults to 1, which is < 5 → Retry
        with pytest.raises(Retry) as exc_info:
            await failing_task({})

        assert exc_info.value.defer == 10  # 1 * 10

    async def test_log_args_does_not_affect_result(self):
        @arq_task(log_args=True)
        async def my_task(ctx, x, y):
            return x + y

        result = await my_task({"job_try": 1}, 3, 4)
        assert result == 7

    async def test_preserves_function_name(self):
        @arq_task()
        async def my_special_task(ctx):
            return "ok"

        assert my_special_task.__name__ == "my_special_task"

    async def test_first_try_retry_backoff(self):
        @arq_task(retry_backoff=30, max_retries=5)
        async def failing_task(ctx):
            raise RuntimeError("fail")

        with pytest.raises(Retry) as exc_info:
            await failing_task({"job_try": 1})

        assert exc_info.value.defer == 30  # 1 * 30
