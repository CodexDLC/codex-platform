# codex-platform

[![PyPI version](https://img.shields.io/pypi/v/codex-platform.svg)](https://pypi.org/project/codex-platform/)
[![Python](https://img.shields.io/pypi/pyversions/codex-platform.svg)](https://pypi.org/project/codex-platform/)
[![CI](https://github.com/codexdlc/codex-platform/actions/workflows/ci.yml/badge.svg)](https://github.com/codexdlc/codex-platform/actions/workflows/ci.yml)
[![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](https://www.apache.org/licenses/LICENSE-2.0)

`codex-platform` is a modular, async infrastructure library. Originally built as the foundation for the Codex ecosystem, it is designed from the ground up to be completely independent. You can use it in any Python project to get a typed Redis abstraction, a Redis Streams event bus, structured ARQ background workers, or a multi-channel notification engine. Every component is completely independent and can be installed as a separate extra.

---

## Install

```bash
# codex-platform 0.6.x (after 0.6.0 is published)
pip install "codex-platform>=0.6.0,<0.7.0"

# With Redis support
pip install "codex-platform[redis]>=0.6.0,<0.7.0"

# With ARQ background workers
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

## Development

```bash
uv sync --extra dev
uv run pytest
uv run mypy src/
uv run pre-commit run --all-files
uv build --no-sources
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
| `messaging` | `[notifications]` | Multi-channel notification primitives — SMTP, ARQ/direct delivery, Jinja2 renderer; `notifications` remains a deprecated compatibility import |

## Optional agent skill (starting in 0.6.0)

Starting with `codex-platform` 0.6.0, the package includes an offline coding-agent skill for its Redis, Streams, ARQ, and messaging APIs. Installing the Python package does not change a project. To copy the skill into an existing project, run these commands from the Python environment where `codex-platform` is installed:

```bash
python -m codex_platform.agent_skills install --project /path/to/project
python -m codex_platform.agent_skills status --project /path/to/project
python -m codex_platform.agent_skills update --project /path/to/project
python -m codex_platform.agent_skills delete --project /path/to/project
```

The installer manages `.agents/skills/codex-platform/` and a bounded reference block in the project's root `AGENTS.md`. It preserves unrelated project guidance, tracks package version and file hashes, and refuses to overwrite locally edited managed files. See the [agent skill guide](docs/en/guides/agent-skills.md) for lifecycle and recovery details.

## Documentation

Full docs with architecture, API reference, and data flow diagrams:

**[codexdlc.github.io/codex-platform](https://codexdlc.github.io/codex-platform/)**

## Part of the Codex ecosystem

| Package | Role |
| :--- | :--- |
| [codex-core](https://github.com/codexdlc/codex-core) | Foundation — immutable DTOs, PII masking, env settings |
| **codex-platform** | Infrastructure — Redis, Streams, ARQ workers, messaging |
| [codex-ai](https://github.com/codexdlc/codex-ai) | LLM layer — unified async interface for OpenAI, Gemini, Anthropic |
| [codex-services](https://github.com/codexdlc/codex-services) | Business logic — Booking engine, CRM, Calendar |

Each library is **fully standalone** — install only what your project needs.
Together they form the backbone of **[codex-bot](https://github.com/codexdlc/codex-bot)**
(Telegram AI-agent infrastructure built on aiogram) and
**[codex-django](https://github.com/codexdlc/codex-django)** (Django integration layer).
