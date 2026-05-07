# Changelog

All notable changes to this project will be documented in this file.
Grouped by `Added` · `Changed` · `Deprecated` · `Removed` · `Fixed`.

## [Unreleased]

### Fixed
- Reduced Redis Streams consumer latency by using configurable blocking `XREADGROUP` reads instead of relying on the processor polling interval for normal wakeups.

## [0.5.1] - 2026-04-30

### Fixed
- Fixed GitHub Actions integration environment to install docs dependencies required by the MkDocs build test.
- Stabilized the multi-consumer-group streams integration test by creating Redis consumer groups before publishing the shared event.

## [0.5.0] - 2026-04-30

### Added
- Added `StreamRuntime` and `StreamRuntimeConfig` for grouped Redis Streams workers that can run all handlers in monolith mode or only selected logical groups in split-service mode.
- Added `StreamHandlerSpec` metadata and `group` / `reply` arguments to stream router and dispatcher decorators.
- Added `StreamProducer.publish()`, `StreamProducer.request()`, and `StreamProducer.publish_reply()` for correlation-id based request/reply flows.

### Changed
- Redis Streams payloads now use JSON-safe field encoding for structured values instead of coercing every value to plain `str` or dropping `None`.
- `StreamConsumer` now implements the `StreamStorageProtocol` used by `StreamProcessor` directly.

## [0.4.0] - 2026-04-22

### Added
- Synchronous Redis operations: `SyncStringOperations` and `SyncHashOperations` using `redis.Redis`.
- Added `catch_redis_errors_sync` decorator for synchronous methods.
- Added `encoder` parameter to `HashOperations.set_fields` and `SyncHashOperations.set_fields`.
### Added
- Added `py.typed` marker for PEP 561 compliance — downstream consumers now benefit from full type inference when using mypy or pyright.

### Changed
- Translated all Russian comments and docstrings to English across `redis_service/exceptions.py`, `workers/arq/config.py`, `notifications/registry.py`, and `streams/__init__.py`.

## [0.3.0] - 2026-04-05

### Changed
- Raised the `codex-core` requirement to `>=0.3.0,<0.10.0` so the package tracks the new core baseline while remaining compatible through the `0.9.x` series.
- Updated the documented install examples to the `codex-platform 0.3.x` release line.

## [0.2.0] - 2026-03-29

### Added
- `SiteSettingsManager` as a public Redis manager for shared `site_settings` hash access across services.
- `uv.lock` for reproducible local and CI environments.

### Changed
- Standardized the documentation site around the shared Codex MkDocs layout: English-only API reference, bilingual architecture guides, teal/cyan theme, and shared extra CSS.
- Migrated CI, docs deployment, publishing, and local developer workflows from ad-hoc `pip` installs to `uv`.
- Raised the supported Python baseline to 3.12 and simplified code paths that only existed for Python 3.10/3.11 compatibility.
- Reused shared developer tooling from `codex-core` for project checks and project-tree generation, with `tools/dev/check.py` configured via the new `RUN_*` policy flags.
- Pinned the `codex-core` dependency to the supported `0.2.x` series.
- Enabled the shared pytest/coverage mode in `pyproject.toml` so local runs, CI, and `tools/dev/check.py` all collect coverage consistently.

### Removed
- Duplicated `docs/ru/api` reference pages now that API documentation is published in English only.

### Fixed
- Kept docs-build integration tests aligned with CI by installing docs dependencies in the integration test job.
- Updated landing-page documentation links and examples to match the current docs structure and public API.
- Fixed `BaseWorkerConfig` to inherit settings from `codex-core` correctly and to build ARQ Redis settings from the actual shared Redis fields.
- Stopped standalone integration test runs from failing the release coverage gate by disabling coverage collection for integration-only runs in CI and `tools/dev/check.py`.

## [0.1.0] - 2024-05-30

### Added
- Initial split from monolithic `codex_tools` repository.
- `redis_service` — async Redis abstraction with typed operations (Hash, String, List, Set, ZSet, JSON, Pipeline).
- `streams` — Redis Streams producer/consumer with consumer groups, dispatcher, processor, router, and DLQ via ARQ.
- `notifications` — multi-channel notification engine with ARQ and Direct delivery adapters.
- `workers.arq` — base ARQ worker infrastructure with health check, DLQ retry, and `CORE_FUNCTIONS`.
