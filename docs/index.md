<!-- type: LANDING -->

# codex-platform

Infrastructure library for the Codex WaaS toolkit. Provides background task workers (ARQ), Redis service abstraction, Redis Streams event bus, and framework-independent messaging primitives.

Built to be dropped into any Python 3.12+ service as a set of composable, independently installable extras.

## Install

```bash
# codex-platform 0.6.x (after 0.6.0 is published)
pip install "codex-platform>=0.6.0,<0.7.0"

# With Redis support
pip install "codex-platform[redis]>=0.6.0,<0.7.0"

# With ARQ worker support
pip install "codex-platform[arq]>=0.6.0,<0.7.0"

# With async SMTP notifications
pip install "codex-platform[notifications]>=0.6.0,<0.7.0"

# Redis Streams
pip install "codex-platform[streams]>=0.6.0,<0.7.0"

# Everything
pip install "codex-platform[all]>=0.6.0,<0.7.0"
```

Requires Python 3.12 or newer.
Installs `codex-core>=0.5.0,<0.10.0` automatically as a dependency.
The `0.6.x` examples describe the next release; until it is published, use the [latest available version on PyPI](https://pypi.org/project/codex-platform/).

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

The optional offline [agent skill](en/guides/agent-skills.md) is available starting in 0.6.0. Its installer manages a library-owned skill and a bounded `AGENTS.md` link in an existing project.

| Section | Description |
| :--- | :--- |
| [Guide (EN)](en/architecture/notifications/README.md) | Architecture overviews and data-flow pages in English |
| [Руководство (RU)](ru/architecture/notifications/README.md) | Архитектурные страницы и схемы на русском |
| [API Reference](en/api/index.md) | English-only API reference generated from docstrings |
| [Changelog](changelog.md) | Version history |
