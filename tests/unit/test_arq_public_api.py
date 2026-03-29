"""Tests for codex_platform.workers.arq public exports."""

import pytest

from codex_platform.workers.arq import (
    CORE_FUNCTIONS,
    HEALTH_FILE,
    BaseArqService,
    BaseArqWorkerSettings,
    BaseWorkerConfig,
    DependencyFunction,
    arq_task,
    base_shutdown,
    base_startup,
    requeue_to_stream,
)

pytestmark = pytest.mark.unit


def test_public_exports_are_available():
    assert BaseArqService is not None
    assert BaseArqWorkerSettings is not None
    assert BaseWorkerConfig is not None
    assert HEALTH_FILE is not None
    assert arq_task is not None
    assert base_startup is not None
    assert base_shutdown is not None
    assert requeue_to_stream in CORE_FUNCTIONS
    assert DependencyFunction is not None
