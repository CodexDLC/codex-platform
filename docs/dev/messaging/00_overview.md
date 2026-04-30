# `codex-platform.messaging` — Overview

> **Status**: Phase 0 design document. The package described here is the
> rename + expansion of the existing `codex_platform.notifications` package.
> No code has been written yet; this file is the contract that drives Phase 2
> of the migration roadmap.

## Purpose

`codex_platform.messaging` is the **framework-agnostic core** of the codex
messaging stack. It provides the building blocks that any host framework
(Django, FastAPI, a bare ARQ worker) can compose to send transactional
emails, deliver multi-channel notifications, render templates, and route
inbound replies to a thread.

It deliberately does **not**:

* import any web framework,
* depend on a database,
* know about HTTP request/response objects,
* hold mutable global state beyond a registry of pluggable factories.

If a piece of code needs Django, it does not belong here — it belongs in
`codex_django.messaging`.

## What lives here

| Sub-package | Owns |
|-------------|------|
| `messaging.dto` | Pydantic DTOs that travel across process boundaries (Django ↔ worker, FastAPI ↔ worker). |
| `messaging.channels` | `NotificationChannel` enum (`email`, `sms`, `telegram`, `whatsapp`). |
| `messaging.clients` | Concrete protocol-conforming channel implementations (SMTP, SendGrid HTTP, future Telegram). |
| `messaging.delivery` | Adapters that move a payload to a runtime: ARQ queue, in-process direct send. |
| `messaging.orchestrator` | `BaseDeliveryOrchestrator` — fallback chain over a list of `DeliveryChannel`s. |
| `messaging.registry` | `ChannelRegistry` — config-driven factory list. |
| `messaging.renderer` | Optional Jinja2 renderer for worker-side template mode. |
| `messaging.threading` | Helpers for RFC 5322 `Message-ID`, `In-Reply-To`, `References` and the neutral `X-Codex-Thread-Key` header. |
| `messaging.audience` | `AudienceBuilder` protocol + `RecipientDraft` DTO for mass-mail batching. |
| `messaging.campaigns` | `CampaignDispatcher` protocol + `CampaignBatchDTO` schema for the worker callback contract. |
| `messaging.workers_contract` | Frozen schema versions and task-name constants the worker must keep in sync with. |

## Layer diagram

```
                ┌──────────────────────────────┐
                │ codex_core                    │
                │  - BaseDTO (Pydantic)         │
                │  - settings primitives        │
                └──────────────┬───────────────┘
                               │
                ┌──────────────▼───────────────┐
                │ codex_platform.messaging      │  ← THIS PACKAGE
                │  (framework-agnostic)         │
                └──────┬──────────────────┬─────┘
                       │                  │
       ┌───────────────▼─────┐  ┌─────────▼────────────┐
       │ codex_django.       │  │ future:               │
       │   messaging         │  │ codex_fastapi.        │
       │ (Django adapters)   │  │   messaging           │
       └─────────────────────┘  └──────────────────────┘
                       │                  │
                       └────────┬─────────┘
                                │
                ┌───────────────▼───────────────┐
                │ project apps (lily_backend, …)│
                └───────────────────────────────┘
```

## FastAPI-readiness contract

The whole package must satisfy the following invariants. CI should enforce
each of them with a static check:

1. **No `import django`** anywhere under `src/codex_platform/messaging/`.
2. **No transitive Django pull-in.** All channel/orchestrator/renderer code
   uses `pydantic`, `arq`, `aiosmtplib`, `httpx`, `jinja2` (optional). No
   adapter from another framework is imported eagerly.
3. **All cross-process payloads are Pydantic DTOs** that subclass
   `codex_core.core.BaseDTO`. Plain dicts may be used internally between
   `messaging.delivery.*.enqueue()` and the worker, but every dict must
   round-trip through a DTO at both ends.
4. **All time fields are timezone-aware ISO-8601 strings** in DTOs. The
   package never assumes a global timezone; the host application is
   responsible for the wall-clock interpretation.
5. **All registry entries are functions, not module-level imports.** The
   registry calls factories lazily so an unconfigured channel does not
   force a missing dependency import.

## Two delivery modes (kept from `notifications`, made first-class)

### Mode 1 — Worker-rendered (`TemplateNotificationDTO`)

The host pushes a `template_name` + a Redis context key. The worker fetches
the context, renders the template via Jinja2, then sends.

* **Use when**: content depends on data that may change between enqueue
  and send (booking time, reschedule), or when you want the worker to
  share a single template directory across many hosts.
* **Cost**: worker must have Jinja2 installed and a templates directory.

### Mode 2 — Pre-rendered (`RenderedNotificationDTO`)

The host renders HTML/text in its own template engine and passes the
result on the wire. The worker only delivers.

* **Use when**: the host has Django templates (i18n, request context,
  CMS blocks) and you want exactly the same layout in send and preview.
* **Cost**: payload is larger; you cannot mutate the rendered content
  after enqueue.

The orchestrator and channels do not care which mode produced the
payload — they only see the resolved `html_content` / `text_content`
fields on the DTO.

## What this package does NOT decide

* The shape of recipients, threads, campaigns, or message bodies in a
  database. That is owned by `codex_django.messaging` (abstract models)
  and the project (concrete models).
* The cabinet / admin UI. That is owned by `codex_django.messaging` plus
  project templates.
* Audience selection logic (segmentation, GDPR consent, etc.). The
  package only declares the `AudienceBuilder` protocol; concrete query
  logic belongs in projects.
* Provider-specific identity (sender name, reply-to). Those flow into
  the channel via DTO fields and configuration; the package never
  hard-codes them.

## Open design points (resolved during doc review)

Listed here so future maintainers can find the rationale:

1. **Decorator API for content builders.** Two competing styles —
   split (`@email_template` / `@email_rendered`) and unified
   (`@notification(mode=…)`) — are documented in
   `codex-django/docs/dev/messaging/03_decorators.md`. The platform
   layer is agnostic; it sees only the DTO that comes out the other end.
2. **Inbound transport.** Currently out of scope. The package exposes
   `messaging.threading` so that any inbound transport (IMAP poller,
   webhook, S3 bucket) can attach incoming mail to an existing thread
   using the same headers used on outbound. Concrete inbound transports
   are deferred.
3. **Provider-key storage.** `codex_platform.messaging` never reads
   secrets. SendGrid API key, SMTP password, etc. flow in via the host
   config object. The host MUST keep secrets out of the database; see
   `codex-django/docs/dev/messaging/05_settings_migration.md`.

## Referenced documents

* `01_core_dtos_and_protocols.md` — DTO and protocol catalog.
* `02_channels_and_registry.md` — `DeliveryChannel`, `ChannelRegistry`.
* `03_renderer_and_templates.md` — Jinja2 renderer + template-key
  conventions.
* `04_threading_and_headers.md` — RFC 5322 helpers and the
  `X-Codex-Thread-Key` neutral header.
* `05_workers_contract.md` — task names, payload schema versions.
* `06_migration_from_notifications.md` — concrete rename + alias plan.
