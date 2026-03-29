<!-- type: LANDING -->

# codex-platform

Infrastructure library for the Codex WaaS toolkit. Provides background task workers (ARQ), Redis service abstraction, Redis Streams event bus, and a multi-channel notification engine.

Built to be dropped into any Python 3.12+ service as a set of composable, independently installable extras.

## Install

```bash
# codex-platform 0.2.x
pip install "codex-platform>=0.2.0,<0.3.0"

# With Redis support
pip install "codex-platform[redis]>=0.2.0,<0.3.0"

# With ARQ worker support
pip install "codex-platform[arq]>=0.2.0,<0.3.0"

# With async SMTP notifications
pip install "codex-platform[notifications]>=0.2.0,<0.3.0"

# Redis Streams
pip install "codex-platform[streams]>=0.2.0,<0.3.0"

# Everything
pip install "codex-platform[all]>=0.2.0,<0.3.0"
```

Requires Python 3.12 or newer.
Installs `codex-core>=0.2.0,<0.3.0` automatically as a dependency.

## Quick Start

```python
from redis.asyncio import Redis
from codex_platform.redis_service import RedisService

redis = Redis(host="localhost", port=6379)
service = RedisService(redis)

await service.hash.set_json("user:42", "profile", {"name": "Alex"})
data = await service.hash.get_json("user:42", "profile")
```

<!-- TODO: extract to tasks/ once tasks/ layer is created -->

## Navigation

| Section | Description |
| :--- | :--- |
| [Guide (EN)](en/architecture/notifications/README.md) | Architecture overviews and data-flow pages in English |
| [Руководство (RU)](ru/architecture/notifications/README.md) | Архитектурные страницы и схемы на русском |
| [API Reference](en/api/index.md) | English-only API reference generated from docstrings |
| [Changelog](changelog.md) | Version history |
