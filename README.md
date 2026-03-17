# codex-platform

[![PyPI version](https://img.shields.io/pypi/v/codex-platform.svg)](https://pypi.org/project/codex-platform/)
[![Python](https://img.shields.io/pypi/pyversions/codex-platform.svg)](https://pypi.org/project/codex-platform/)
[![CI](https://github.com/codexdlc/codex-platform/actions/workflows/ci.yml/badge.svg)](https://github.com/codexdlc/codex-platform/actions/workflows/ci.yml)
[![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](LICENSE)

Infrastructure library for the **Codex WaaS toolkit**. Provides async Redis abstraction, Redis Streams event bus, ARQ background workers, and a multi-channel notification engine — each as an independently installable extra.

---

## Install

```bash
# Core only
pip install codex-platform

# With Redis support
pip install "codex-platform[redis]"

# With ARQ background workers
pip install "codex-platform[arq]"

# With async SMTP notifications
pip install "codex-platform[notifications]"

# Redis Streams
pip install "codex-platform[streams]"

# Everything
pip install "codex-platform[all]"
```

## Quick Start

```python
from redis.asyncio import Redis
from codex_platform.redis_service import RedisService

redis = Redis(host="localhost", port=6379)
service = RedisService(redis)

await service.hash.set_json("user:42", "profile", {"name": "Alex"})
data = await service.hash.get_json("user:42", "profile")
```

## Modules

| Module | Extra | Description |
| :--- | :--- | :--- |
| `redis_service` | `[redis]` | Typed async Redis abstraction — Hash, String, List, Set, ZSet, JSON, Pipeline |
| `streams` | `[streams]` | Redis Streams producer/consumer with consumer groups, retry, and DLQ |
| `workers.arq` | `[arq]` | ARQ worker base infrastructure — health probes, DLQ retry, CORE_FUNCTIONS |
| `notifications` | `[notifications]` | Multi-channel notification engine — SMTP, ARQ/Direct delivery, Jinja2 renderer |

## Documentation

Full docs with architecture, API reference, and data flow diagrams:

**[codexdlc.github.io/codex-platform](https://codexdlc.github.io/codex-platform/)**

## Part of the Codex ecosystem

[codex-core](https://github.com/codexdlc/codex-core) · **codex-platform** · [codexdlc](https://github.com/codexdlc)
