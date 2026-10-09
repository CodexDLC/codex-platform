---
name: codex-platform-maintainer
description: Use for maintaining this repository's Redis, Streams, ARQ, messaging, packaging, or release integration.
---

# codex-platform maintenance

This repository publishes the `codex-platform` library. Keep framework-independent infrastructure in `src/codex_platform/`; application policy and business rules belong to consumers. The public API is exposed by each component's `__init__.py`. Inspect those exports and the corresponding unit tests before changing a contract.

Components are independent optional surfaces: `redis_service` needs Redis, `streams` uses Redis Streams, `workers.arq` needs ARQ, and `messaging` handles notification primitives. `notifications` is deprecated compatibility code; new behavior belongs in `messaging` and compatibility changes need explicit tests.

The canonical consumer skill lives in `src/codex_platform/agent_skills/resources/`. Treat its installed copies in other projects as managed output. When changing installer behavior, exercise install, update, delete, and status in a temporary consumer directory and inspect wheel and sdist payloads. Run focused tests and configured lint/types for affected code. The root `AGENTS.md` requires refreshing the shared graph after code changes.
