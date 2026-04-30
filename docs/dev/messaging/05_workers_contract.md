# Worker Contract

This document is the frozen schema and behavior contract that any worker
processing `codex_platform.messaging` payloads MUST honor. The lily
`notification_worker` is the reference implementation; future workers
(per-project or for a different host stack) MUST keep the same surface.

## Task names (canonical)

| Task name | Purpose | DTO | Defined in |
|-----------|---------|-----|------------|
| `send_universal_notification_task` | Single notification, either mode. | `TemplateNotificationDTO` or `RenderedNotificationDTO` (the worker dispatches by `mode` field) | `src/workers/notification_worker/tasks/notification_tasks.py:201` |
| `send_rendered_notification_task` | Pre-rendered convenience task. Optional; `send_universal_notification_task` covers it. | `RenderedNotificationDTO` | `tasks/notification_tasks.py:247` |
| `send_campaign_batch_task` | One batch of campaign recipients. | `CampaignBatchDTO` | `src/workers/notification_worker/tasks/campaign_tasks.py:1` |
| `send_group_booking_notification_task` | Legacy. Reads booking group from Redis cache. | (legacy payload) | `tasks/notification_tasks.py:284` |

The canonical names are constants in `messaging.workers_contract`:

```python
TASK_SEND_NOTIFICATION = "send_universal_notification_task"
TASK_SEND_RENDERED     = "send_rendered_notification_task"
TASK_SEND_CAMPAIGN     = "send_campaign_batch_task"
```

Hosts MUST import these constants instead of hard-coding strings.

## Payload schema versioning

A new top-level field `schema_version: int` is added to all DTOs.
Initial value: `1`. Incompatible changes (renames, removals, type
changes) bump the version. Workers MAY refuse to process payloads
whose `schema_version` is higher than the worker's supported version
and MUST log a clear error.

The version is checked **before** Pydantic validation so that a worker
that is rolling forward can short-circuit instead of getting validation
errors.

## Retry contract

The lily worker retries with exponential backoff:

```python
defer = job_try * 30s   # 30s, 60s, 90s, 120s, 150s
max_tries = 5
```

This contract is documented as the platform default. Workers MAY tune
the schedule but MUST:

1. Use bounded retries — no infinite retry loop.
2. Emit a final-failure callback (see below) on the last attempt.
3. Never retry on `400 Bad Request`-class errors (validation, auth);
   those are permanent and retrying just amplifies the failure.

## Worker → host callbacks

Two callback shapes:

### Per-recipient delivery status (campaign)

`POST {callback_url}` with payload:

```json
{
  "notification_id": "campaign_<campaign_id>_<recipient_pk>",
  "status": "sent|failed|bounced|unsubscribed",
  "error": "string|null",
  "provider_message_id": "string|null"
}
```

* `notification_id` matches what the host put in the batch DTO.
* `status` MUST be one of the four enumerated values.
* `error` is non-null only on `failed` and `bounced`.
* `provider_message_id` is the upstream provider's tracking ID
  (SMTP server response code, SendGrid x-message-id) — opaque to the
  platform; useful for support investigations.

The host validates `callback_token` (today: `OPS_WORKER_API_KEY` scoped
to `"campaigns.worker"` in
`src/lily_backend/system/api/auth.py:12-18`).

### Single-notification delivery status (event-based)

`POST /messaging/notifications/status` with the same shape minus
`provider_message_id`. The host writes an `EmailLog` row keyed by
`notification_id`.

This callback is **new in the messaging refactor**. The current
`notification_worker` only calls back on campaign failure. Single
notifications today succeed silently — there is no audit trail. The
new contract requires every send to call back on:

* Final success.
* Final failure (after retries exhausted).

The worker MUST NOT call back on intermediate retry attempts.

## Idempotency

`notification_id` is the **idempotency key** across host and worker.

* The host MUST use a stable, content-derived value (hash of campaign
  + recipient + send_at, UUID stored in the originating record, etc.).
* The worker SHOULD deduplicate at-most-once by checking a Redis set:
  if `notification_id` was processed within N hours, skip.
* The host MUST tolerate seeing the same callback multiple times
  (network retries) — the `EmailLog` write SHOULD be idempotent on
  `notification_id`.

The current lily worker does not deduplicate. The migration adds an
optional Redis `seen` cache; configurable per worker.

## Configuration the worker reads

The worker MUST receive all configuration via:

1. **Environment variables** (worker boot config): `SMTP_HOST`,
   `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`, `SMTP_FROM_EMAIL`,
   `SMTP_USE_TLS`, `SMTP_USE_SSL`, `SENDGRID_API_KEY`, `TEMPLATES_DIR`.
2. **Redis hash** (host-managed, dynamic): the canonical hash key is
   `email_settings:` (renamed from `site_settings:` — see
   `lily_website/docs/dev/messaging_migration/04_workers_alignment.md`).
   The hash contains the runtime-mutable identity fields:
   `email_from`, `email_sender_name`, `email_reply_to`,
   `site_base_url`, `logo_url`, `url_path_*`.

The worker MUST NOT read from a Django ORM, the host's database, or any
host-private storage. The Redis hash is the single channel for
host → worker configuration changes that don't require a worker
restart.

## Worker → ARQ contract

Tasks are registered via `WorkerSettings.functions`. The lily worker
gets the function list from `task_aggregator.py`:

```python
from codex_platform.workers.arq import CORE_FUNCTIONS

FUNCTIONS = [
    *CORE_FUNCTIONS,
    send_universal_notification_task,
    send_rendered_notification_task,
    send_campaign_batch_task,
    # legacy:
    send_group_booking_notification_task,
]
```

The platform contract is:

* The host enqueues with `pool.enqueue_job(task_name, payload_dict=…)`.
* The worker receives `(ctx, payload_dict=…)` and validates the dict
  through the appropriate DTO.
* The worker returns nothing useful to ARQ — completion is signaled via
  the host callback (or via `EmailLog` row in the future).

## Anti-patterns

* **Reading config off `django.conf.settings` from inside a worker
  task.** The worker MUST NOT import Django. Configuration flows
  through env + Redis only.
* **Inlining HTML rendering in the campaign batch loop.** The campaign
  batch task pushes per-recipient sub-jobs back into the queue rather
  than rendering inline; this preserves bounded job duration and lets
  ARQ retry per-recipient.
* **Calling back on every retry.** The host has no way to distinguish
  retry-success from retry-failure if both produce callbacks. Call
  back only on terminal outcomes.
