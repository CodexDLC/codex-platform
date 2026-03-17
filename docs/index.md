<!-- type: LANDING -->

# codex-platform

Infrastructure library for the Codex WaaS toolkit. Provides background task workers (ARQ), Redis service abstraction, Redis Streams event bus, and a multi-channel notification engine.

Built to be dropped into any Python 3.12+ service as a set of composable, independently installable extras.

## Install

```bash
# Core only (Pydantic + loguru)
pip install codex-platform

# With Redis support
pip install codex-platform[redis]

# With ARQ worker support
pip install codex-platform[arq]

# With async SMTP notifications
pip install codex-platform[notifications]

# Everything
pip install codex-platform[all]
```

## Quickstart

```python
from redis.asyncio import Redis
from codex_platform.redis_service import RedisService

redis = Redis(host="localhost", port=6379)
service = RedisService(redis)

await service.hash.set_json("user:42", "profile", {"name": "Alex"})
```

<!-- TODO: extract to tasks/ once tasks/ layer is created -->

## Navigation

| Section | Description |
| :--- | :--- |
| [Architecture](architecture/notifications/README.md) | Design decisions, data flows, module philosophy |
| [API Reference](api/index.md) | Auto-generated from docstrings |
| [Changelog](changelog.md) | Version history |
