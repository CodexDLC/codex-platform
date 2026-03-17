"""Tests for codex_platform.redis_service.operations.pipeline — PipelineOperations."""

import pytest

from codex_platform.redis_service.operations import PipelineOperations

pytestmark = pytest.mark.unit


@pytest.fixture
def ops(redis_client):
    return PipelineOperations(redis_client)


class TestExecute:
    async def test_batch_execution(self, ops, redis_client):
        async def build(pipe):
            await pipe.set("k1", "v1")
            await pipe.set("k2", "v2")

        results = await ops.execute(build)
        assert len(results) == 2
        assert await redis_client.get("k1") == "v1"
        assert await redis_client.get("k2") == "v2"


class TestTransact:
    async def test_atomic_transaction(self, ops, redis_client):
        async def build(pipe):
            await pipe.set("k1", "v1")
            await pipe.set("k2", "v2")

        results = await ops.transact(build)
        assert len(results) == 2
        assert await redis_client.get("k1") == "v1"
        assert await redis_client.get("k2") == "v2"


class TestEvalScript:
    async def test_lua_set_and_return(self, ops, redis_client):
        script = "redis.call('SET', KEYS[1], ARGV[1]); return 1"
        result = await ops.eval_script(script, keys=["lua_key"], args=["lua_val"])
        assert result == 1
        assert await redis_client.get("lua_key") == "lua_val"

    async def test_lua_no_keys(self, ops):
        result = await ops.eval_script("return 42")
        assert result == 42
