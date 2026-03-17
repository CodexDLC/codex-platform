# Changelog

All notable changes to this project will be documented in this file.
Grouped by `Added` · `Changed` · `Deprecated` · `Removed` · `Fixed`.

## [0.1.0] - 2024-05-30

### Added
- Initial split from monolithic `codex_tools` repository.
- `redis_service` — async Redis abstraction with typed operations (Hash, String, List, Set, ZSet, JSON, Pipeline).
- `streams` — Redis Streams producer/consumer with consumer groups, dispatcher, processor, router, and DLQ via ARQ.
- `notifications` — multi-channel notification engine with ARQ and Direct delivery adapters.
- `workers.arq` — base ARQ worker infrastructure with health check, DLQ retry, and `CORE_FUNCTIONS`.
