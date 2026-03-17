"""
codex_platform.worker.arq.task_utils
====================================
Utilities for writing ARQ tasks with less boilerplate.

Usage:
    from codex_platform.worker.arq import arq_task

    @arq_task(retry_backoff=60, max_retries=3)
    async def send_booking_notification(ctx, appointment_id: int):
        service = ctx["notification_service"]
        await service.send(...)
"""

import logging
from functools import wraps
from typing import Any

from arq import Retry

log = logging.getLogger(__name__)


def arq_task(
    *,
    retry_backoff: int = 30,
    max_retries: int = 5,
    log_args: bool = False,
) -> Any:
    """
    Decorator that adds standard error handling, logging, and retry to ARQ tasks.

    Args:
        retry_backoff: Base delay in seconds. Actual delay = job_try * retry_backoff.
        max_retries: Maximum number of retries before giving up.
        log_args: If True, log task arguments (be careful with PII).

    Wrapped function receives ctx as first arg (standard ARQ convention).
    On exception:
        - If job_try < max_retries → raises Retry(defer=job_try * retry_backoff)
        - If job_try >= max_retries → logs error and returns None (task dropped)
    """

    def decorator(fn: Any) -> Any:
        @wraps(fn)
        async def wrapper(ctx: dict[str, Any], *args: Any, **kwargs: Any) -> Any:
            task_name = fn.__name__
            job_try = ctx.get("job_try", 1)

            if log_args:
                log.info("%s | start | try=%d | args=%s kwargs=%s", task_name, job_try, args, kwargs)
            else:
                log.info("%s | start | try=%d", task_name, job_try)

            try:
                result = await fn(ctx, *args, **kwargs)
                log.info("%s | success | try=%d", task_name, job_try)
                return result
            except Retry:
                raise
            except Exception as e:
                if job_try < max_retries:
                    defer = job_try * retry_backoff
                    log.warning("%s | retry in %ds | try=%d | error=%s", task_name, defer, job_try, e)
                    raise Retry(defer=defer) from e
                log.exception("%s | max retries (%d) reached | giving up", task_name, max_retries)
                return None

        wrapper.__qualname__ = fn.__qualname__
        return wrapper

    return decorator
