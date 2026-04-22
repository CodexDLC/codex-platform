from unittest.mock import MagicMock

import fakeredis
import fakeredis.aioredis
import pytest
from redis.exceptions import ConnectionError, RedisError

from codex_platform.redis_service.exceptions import RedisConnectionError, RedisServiceError
from codex_platform.redis_service.operations.hash import HashOperations
from codex_platform.redis_service.operations.sync_hash import SyncHashOperations
from codex_platform.redis_service.operations.sync_string import SyncStringOperations

pytestmark = pytest.mark.unit


@pytest.fixture
def sync_client():
    return fakeredis.FakeRedis(decode_responses=True)


@pytest.fixture
def sync_string_ops(sync_client):
    return SyncStringOperations(sync_client)


@pytest.fixture
def sync_hash_ops(sync_client):
    return SyncHashOperations(sync_client)


def test_sync_string_operations(sync_string_ops):
    sync_string_ops.set("test_key", "value")
    assert sync_string_ops.get("test_key") == "value"

    sync_string_ops.set("test_key", "value2", ttl=60)
    assert sync_string_ops.get("test_key") == "value2"
    assert sync_string_ops.ttl("test_key") > 0

    assert sync_string_ops.exists("test_key") is True
    sync_string_ops.delete("test_key")
    assert sync_string_ops.exists("test_key") is False
    assert sync_string_ops.get("test_key") is None

    sync_string_ops.mset({"k1": "v1", "k2": "v2"})
    assert sync_string_ops.mget("k1", "k2", "k3") == ["v1", "v2", None]

    sync_string_ops.set("counter", "1")
    assert sync_string_ops.incr("counter") == 2

    sync_string_ops.expire("counter", 10)
    assert sync_string_ops.ttl("counter") > 0


def test_sync_hash_operations(sync_hash_ops):
    sync_hash_ops.set_field("hkey", "f1", "v1")
    assert sync_hash_ops.get_field("hkey", "f1") == "v1"

    sync_hash_ops.set_fields("hkey", {"f2": "v2", "f3": "v3"})
    assert sync_hash_ops.get_all("hkey") == {"f1": "v1", "f2": "v2", "f3": "v3"}

    assert sync_hash_ops.get_fields("hkey", "f1", "f2", "f4") == ["v1", "v2", None]

    assert sync_hash_ops.exists_field("hkey", "f3") is True
    assert sync_hash_ops.exists_field("hkey", "f4") is False

    assert sorted(sync_hash_ops.keys("hkey")) == ["f1", "f2", "f3"]
    assert sorted(sync_hash_ops.values("hkey")) == ["v1", "v2", "v3"]
    assert sync_hash_ops.length("hkey") == 3

    sync_hash_ops.set_field("hkey", "num", "10")
    assert sync_hash_ops.increment("hkey", "num", 5) == 15

    assert sync_hash_ops.delete_field("hkey", "f1", "f2") == 2
    assert sync_hash_ops.get_all("hkey") == {"f3": "v3", "num": "15"}

    sync_hash_ops.delete("hkey")
    assert sync_hash_ops.get_all("hkey") is None


def test_sync_hash_operations_encoder(sync_hash_ops):
    def test_encoder(val):
        return f"enc_{val}"

    sync_hash_ops.set_fields("hkey2", {"f1": "v1", "f2": "v2"}, encoder=test_encoder)
    assert sync_hash_ops.get_all("hkey2") == {"f1": "enc_v1", "f2": "enc_v2"}


def test_sync_operations_error_handling():
    mock_client = MagicMock()
    mock_client.get.side_effect = ConnectionError("Fail")
    mock_client.hget.side_effect = RedisError("Fail")

    string_ops = SyncStringOperations(mock_client)
    hash_ops = SyncHashOperations(mock_client)

    with pytest.raises(RedisConnectionError):
        string_ops.get("key")

    with pytest.raises(RedisServiceError):
        hash_ops.get_field("key", "field")


@pytest.mark.asyncio
async def test_async_hash_operations_encoder():
    async_client = fakeredis.aioredis.FakeRedis(decode_responses=True)
    async_hash_ops = HashOperations(async_client)

    def test_encoder(val):
        return f"enc_{val}"

    await async_hash_ops.set_fields("hkey_async", {"f1": "v1", "f2": "v2"}, encoder=test_encoder)
    assert await async_hash_ops.get_all("hkey_async") == {"f1": "enc_v1", "f2": "enc_v2"}
