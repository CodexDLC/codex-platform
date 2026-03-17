<!-- type: CONCEPT -->


# Redis Service

## Purpose

`redis_service` is a typed, async abstraction over `redis-py`. It replaces raw `await client.hset(...)` calls with structured, error-safe operation classes and key template system.

## Why it's a Service

Direct use of `redis-py` scatters key strings across the codebase and has no consistent error handling. Two problems this module solves:

1. **Key safety** — `BaseRedisKey` templates enforce key structure at construction time. Typos in key prefixes become type errors.
2. **Error containment** — Each operation wraps Redis calls in typed exceptions (`RedisConnectionError`, `RedisServiceError`). Callers know exactly what can fail and why.

## Architecture

```
RedisService (composition root)
   ├── hash        → HashOperations
   ├── string      → StringOperations
   ├── list        → ListOperations
   ├── set         → SetOperations
   ├── zset        → ZSetOperations
   ├── json        → JsonStringOperations   (standard Redis, no extra modules)
   ├── json_module → JsonModuleOperations   (requires RedisJSON server module)
   └── pipeline    → PipelineOperations

All operations receive the same redis.asyncio.Redis client.
Selective composition: use Operations classes directly if you don't need all types.
```

## Key Components

| Component | Module | Role |
| :--- | :--- | :--- |
| `RedisService` | `service.py` | Full composition root — all operations in one object |
| `BaseRedisKey` | `keys.py` | Key template base class |
| `HashOperations` | `operations/hash.py` | HSET / HGET / HGETALL / HDEL |
| `StringOperations` | `operations/string.py` | SET / GET / DELETE with TTL |
| `ListOperations` | `operations/list_.py` | LPUSH / RPUSH / LRANGE / LTRIM |
| `SetOperations` | `operations/set_.py` | SADD / SMEMBERS / SREM / SISMEMBER |
| `ZSetOperations` | `operations/zset.py` | ZADD / ZRANGE / ZRANGEBYSCORE / ZREM |
| `JsonStringOperations` | `operations/json_string.py` | JSON via SET/GET + json.dumps/loads, works with any Redis |
| `JsonModuleOperations` | `operations/json_module.py` | JSON.SET / JSON.GET via RedisJSON server module |
| `PipelineOperations` | `operations/pipeline.py` | Atomic multi-command batches |
| `BaseManager` | `managers/base_manager.py` | Higher-level domain manager base |

## Key Design Decisions

- **Composition over inheritance** — `RedisService` composes operations; it does not subclass them. Use operations directly for selective composition.
- **Typed exceptions** — `RedisConnectionError` for network failures, `RedisServiceError` for all other Redis errors. Never raises raw `redis.exceptions.*` to callers.
- **No connection management** — the module accepts an already-constructed `redis.asyncio.Redis` client. Lifecycle (connect/disconnect) is the caller's responsibility.
- **Two JSON strategies** — `JsonStringOperations` (via `service.json`) works with any Redis using plain string serialization. `JsonModuleOperations` (via `service.json_module`) uses the RedisJSON server module for path-based access and atomic updates.

<!-- TODO: extract to tasks/using_redis_service.md -->

## See Also

- [Data Flow →](data_flow.md)
- [API Reference →](../../../api/redis_service/index.md)
