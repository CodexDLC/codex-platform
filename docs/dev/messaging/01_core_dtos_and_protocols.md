# Core DTOs and Protocols

This document is the canonical reference for every type that crosses a
process boundary in the `codex_platform.messaging` stack. All DTOs inherit
from `codex_core.core.BaseDTO` (Pydantic v2 with PII auto-masking in
`__repr__`). All protocols are `typing.Protocol` so that adapters can be
implemented in any framework without import gymnastics.

## 1. `messaging.channels`

```python
class NotificationChannel(StrEnum):
    EMAIL = "email"
    TELEGRAM = "telegram"
    SMS = "sms"
    WHATSAPP = "whatsapp"
```

* `StrEnum` (Python 3.11+) so JSON round-trip is implicit.
* New channels MUST be added to this enum before being used in any DTO;
  the worker validates payload `channels` against the enum.

## 2. `messaging.dto`

### `NotificationRecipient`

```python
class NotificationRecipient(BaseDTO):
    email: str | None = None
    phone: str | None = None
```

* Both fields are optional but the orchestrator requires at least one to
  resolve a destination address; a payload with neither will be logged
  and dropped.
* PII is masked in `__repr__` by `BaseDTO`.

### `NotificationPayloadDTO` (base)

```python
class NotificationPayloadDTO(BaseDTO):
    notification_id: str
    recipient: NotificationRecipient
    channels: list[NotificationChannel] = [NotificationChannel.EMAIL]
    event_type: str | None = None
    subject: str | None = None
```

* `notification_id` is opaque to the platform and is the **only** primary
  key used to correlate worker callbacks with host-side records. Hosts
  MUST assign an idempotent value (UUID or content hash) — never an
  auto-incremented database PK.
* `event_type` is a free-form domain key (`booking.confirmed`,
  `conversations.compose_new`, …). The worker emits it back on retry
  callbacks so the host can route delivery status updates to the right
  feature.
* `subject` is set by the host — the platform never derives it.

### `TemplateNotificationDTO`

```python
class TemplateNotificationDTO(NotificationPayloadDTO):
    template_name: str
    context_key: str
```

* `template_name` is a path relative to the worker's templates directory
  (e.g. `booking/bk_confirmation.html`). The platform itself does not
  validate the path; the renderer raises `TemplateNotFound` on send.
* `context_key` is a Redis key where a JSON-serialized context is stored.
  Storing context out-of-band keeps the queue payload small and lets the
  host update context after enqueue (reschedule a booking, re-render).

### `RenderedNotificationDTO`

```python
class RenderedNotificationDTO(NotificationPayloadDTO):
    html_content: str
    text_content: str | None = None
```

* `html_content` is the final HTML to be delivered. The orchestrator
  passes it verbatim to the channel.
* `text_content` is the optional plain-text alternative. If absent, the
  channel emits a generic fallback string ("Please enable HTML to view
  this email.").

### `ThreadHeadersDTO` *(new in messaging)*

Promoted out of the worker's `_mailbox_headers()` helper into a real
DTO so it can be composed with both notification DTOs:

```python
class ThreadHeadersDTO(BaseDTO):
    message_id: str             # RFC 5322 Message-ID, host-issued
    in_reply_to: str | None = None
    references: list[str] = []
    thread_key: str             # opaque per-thread token (was X-Lily-Thread-Key)
    reply_match_token: str | None = None  # token routed back via Reply-To
```

The two notification DTOs gain an optional `headers: ThreadHeadersDTO | None`
field. The SMTP / SendGrid channels read it and emit the corresponding
RFC 5322 headers; channels that don't support headers (SMS, Telegram)
ignore the field.

### `CampaignBatchDTO` *(new in messaging)*

Replaces the ad-hoc batch payload that
`features/conversations/tasks/campaign_tasks.py` consumes today.

```python
class CampaignRecipientDraft(BaseDTO):
    recipient_id: str
    email: str
    first_name: str = ""
    last_name: str = ""
    locale: str = "de"
    unsubscribe_token: str | None = None

class CampaignBatchDTO(BaseDTO):
    campaign_id: str
    template_name: str | None = None
    html_content: str | None = None
    subject: str
    recipients: list[CampaignRecipientDraft]
    base_context: dict[str, Any] = {}     # site_url, logo_url, etc.
    callback_url: str                     # where the worker reports recipient status
    callback_token: str                   # opaque, host-issued
```

* Either `template_name` (template mode) or `html_content` (rendered
  mode) MUST be set — the worker rejects a batch with both or neither.
* `callback_url` + `callback_token` decouple the worker from any
  framework: the worker only knows where to POST. The host validates
  the token (currently `OPS_WORKER_API_KEY` scoped to
  `"campaigns.worker"` in lily, see `system/api/auth.py:12-18`).

## 3. `messaging.interfaces`

### `ContentProvider`

```python
class ContentProvider(Protocol):
    def get_text(self, key: str) -> str | None: ...
```

Used by selectors to translate subject / body keys to localized strings.
The Django adapter wraps `django.utils.translation`; a FastAPI adapter
will wrap `babel`.

### `ContentCacheAdapter`

```python
class ContentCacheAdapter(Protocol):
    def get_cached_value(self, key: str) -> str | None: ...
    def set_cached_value(self, key: str, value: str, timeout: int) -> None: ...
```

The platform never imports a cache backend directly. The Django adapter
wraps `django.core.cache`; a FastAPI adapter will wrap `redis-py` or
`aiocache`.

## 4. `messaging.orchestrator`

### `DeliveryChannel`

```python
class DeliveryChannel(Protocol):
    async def send(
        self,
        to: str,
        subject: str,
        html_content: str | None,
        text_content: str | None,
    ) -> bool: ...
    def is_available(self) -> bool: ...
```

* Implementations: `AsyncEmailClient` (SMTP), `SendGridChannel` (HTTP),
  future `TelegramChannel`, `TwilioSmsChannel`.
* `is_available()` MUST be cheap — it is called on every dispatch to
  decide whether to skip the channel.
* `send()` returns `False` for *logical* failures (recipient rejected,
  rate-limit exceeded). It MUST raise on infrastructure failures so the
  orchestrator can fall through to the next channel.

> **Open question**: the current signature does not accept
> `ThreadHeadersDTO`. The migration adds an optional `headers` keyword
> argument. Channels that don't support headers (SMS, Telegram) ignore
> it. Documented in `02_channels_and_registry.md`.

### `BaseDeliveryOrchestrator`

```python
class BaseDeliveryOrchestrator:
    def __init__(self, channels: list[DeliveryChannel]) -> None: ...
    async def deliver(self, payload: NotificationPayloadDTO) -> bool: ...
```

* Pure: only logs and tries channels in order.
* Stops on the first `True` return.
* Logs and falls through on any raised exception.
* Returns `False` if every channel is exhausted.
* Does **not** persist anything — the host (or `EmailLog` writer in the
  Django adapter) is responsible for delivery audit.

## 5. `messaging.delivery`

### `NotificationAdapter`

```python
class NotificationAdapter(Protocol):
    def enqueue(self, task_name: str, payload: dict[str, Any]) -> str | None: ...
```

* Implementations: `ArqNotificationAdapter`, `DirectNotificationAdapter`.
* Returns a job/task ID when the transport supports tracking; `None`
  otherwise.
* Infrastructure errors propagate.

## 6. `messaging.audience` *(new in messaging)*

### `AudienceBuilder` Protocol

```python
class AudienceBuilder(Protocol):
    def count(self, audience_filter: dict[str, Any]) -> int: ...
    def materialize(
        self, audience_filter: dict[str, Any]
    ) -> Iterable[CampaignRecipientDraft]: ...
```

* The filter is a JSON-serializable dict — its shape is project-defined
  (lily uses `consent_marketing`, `locales`, `service_ids`,
  `has_appointment_since`).
* `materialize()` MUST stream — the Django implementation already uses
  `iterator(chunk_size=500)`. The platform documents this expectation;
  it is not enforceable in a Protocol.

### `CampaignDispatcher` Protocol

```python
class CampaignDispatcher(Protocol):
    def enqueue_batch(self, batch: CampaignBatchDTO) -> str: ...
```

The lily implementation today (`features/conversations/campaigns/dispatcher.py`)
returns the ARQ `job_id`. Documented identical here.

## Migration table

| Old (`notifications`) | New (`messaging`) | Notes |
|-----------------------|-------------------|-------|
| `NotificationPayloadDTO` | `NotificationPayloadDTO` | Unchanged. |
| `TemplateNotificationDTO` | `TemplateNotificationDTO` | Unchanged. |
| `RenderedNotificationDTO` | `RenderedNotificationDTO` | Unchanged. |
| `NotificationRecipient` | `NotificationRecipient` | Unchanged. |
| `NotificationChannel` | `NotificationChannel` | Unchanged. |
| `DeliveryChannel` | `DeliveryChannel` | Adds optional `headers` kwarg. |
| `ContentProvider` / `ContentCacheAdapter` | unchanged | Unchanged. |
| *(new)* | `ThreadHeadersDTO` | Promoted from worker helper. |
| *(new)* | `CampaignRecipientDraft`, `CampaignBatchDTO` | Currently lives in lily. |
| *(new)* | `AudienceBuilder`, `CampaignDispatcher` | Currently lives in lily. |

The legacy import path `codex_platform.notifications.<X>` MUST keep
working for at least one minor release; see `06_migration_from_notifications.md`.
