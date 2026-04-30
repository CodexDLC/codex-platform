# Channels and Channel Registry

## What a "channel" is

A `DeliveryChannel` is a single provider-specific transport: SMTP,
SendGrid HTTP API, Twilio SMS, Telegram bot, etc. Channels are
stateless from the orchestrator's perspective — they hold connection
config but no per-request state.

The orchestrator (`BaseDeliveryOrchestrator`) does not know how many
channels exist or in which order they should be tried — that is the
**registry's** job.

## Channel contract (final)

```python
class DeliveryChannel(Protocol):
    async def send(
        self,
        to: str,
        subject: str,
        html_content: str | None,
        text_content: str | None,
        headers: ThreadHeadersDTO | None = None,   # new
    ) -> bool: ...

    def is_available(self) -> bool: ...
```

* **Returns `True`** — the message was accepted by the provider.
* **Returns `False`** — recipient was rejected for a *logical* reason
  (suppression list, invalid address). The orchestrator stops; the next
  channel will not be tried.
* **Raises** — infrastructure error (DNS, TLS, connection refused, 5xx
  from a HTTP API). The orchestrator logs and tries the next channel.
* **`headers` ignored** when the channel cannot carry RFC 5322 headers
  (SMS, Telegram, WhatsApp). The orchestrator never inspects the field.

## Built-in channels

### `clients.smtp.AsyncEmailClient`

* Existing implementation — covered in
  `codex_platform/notifications/clients/smtp.py`.
* `is_available()` returns `True` iff `smtp_host` is set and not
  `localhost`.
* Constructor takes raw config: `smtp_host`, `smtp_port`, `smtp_user`,
  `smtp_password`, `smtp_from_email`, `smtp_use_tls`.
* Uses `aiosmtplib`. SSL/STARTTLS auto-detected from port (465 → SSL,
  587 → STARTTLS).
* **Migration delta**: gain `smtp_from_name` parameter. Today the
  rendered `From:` header uses the email-only form because the field
  does not exist. The host is responsible for passing a non-empty
  display name (typically `EmailSettings.email_sender_name`).

### `clients.sendgrid.SendGridChannel` *(new, promoted from worker)*

* Today the SendGrid logic lives in
  `src/workers/core/base_module/email_client.py:103-129` and is
  hard-wired to `"LILY Beauty Salon"` as the sender name (line 113).
* Promotion plan:
  1. Move the HTTP POST + payload assembly into a new
     `clients/sendgrid.py` module.
  2. Add it as a registered channel in `ChannelRegistry`. The factory
     returns `None` when `SENDGRID_API_KEY` is missing.
  3. Read sender name from the constructor argument; never hard-code.

### Future channels

The package only documents the contract. Concrete `TelegramChannel`,
`TwilioSmsChannel`, etc. live in `codex_platform.messaging.clients.*`
when added. Each new channel MUST:

1. Implement `DeliveryChannel`.
2. Provide a `register_*_channel(registry, config)` helper.
3. Add an entry to the migration table in
   `01_core_dtos_and_protocols.md`.

## `ChannelRegistry` (unchanged behavior, documented expectations)

```python
class ChannelRegistry:
    def register(
        self,
        name: str,
        factory: Callable[[Any], DeliveryChannel | None],
    ) -> None: ...

    def build_channels(self, config: Any) -> list[DeliveryChannel]: ...
```

* `name` is for logging only; duplicates are allowed but the registry
  emits a `WARNING`.
* The factory MUST return `None` (not raise) when the channel cannot be
  configured (missing API key, missing host, etc.). The registry treats
  exceptions raised inside the factory as registration failures and
  logs them via `log.exception`.
* `build_channels(config)` calls every factory in registration order
  and includes channels that are both non-`None` and report
  `is_available() == True`. The result is the ordered list passed to
  `BaseDeliveryOrchestrator`.

### Recommended registration order

```python
registry = ChannelRegistry()
registry.register("smtp",      smtp_factory)       # primary
registry.register("sendgrid",  sendgrid_factory)   # fallback
# (future) registry.register("amazon_ses", ses_factory)
```

The orchestrator stops on the first `True` so the **primary** channel
must be the lowest-cost / highest-trust transport (typically the
project's own SMTP). Fallbacks come after.

## Fallback semantics — explicit

The orchestrator currently treats any thrown exception as
"try next channel". That is the right default, but channels MUST be
careful to:

* Raise for recoverable infrastructure failures (network, TLS, 5xx).
* Return `False` for permanent rejections (invalid recipient,
  suppression). Returning `False` stops the chain — this is correct
  because retrying with a fallback would just re-deliver to a rejected
  address.
* **Never** silently swallow exceptions. The orchestrator's audit log
  is the only signal the host has that the chain failed.

## SendGrid hardcoded-sender bug — explicit fix

`src/workers/core/base_module/email_client.py:113` reads:

```python
"from": {"email": from_email, "name": "LILY Beauty Salon"}
```

The migration moves this code into `clients/sendgrid.py` and accepts
`from_name` via constructor:

```python
class SendGridChannel:
    def __init__(self, *, api_key: str, from_email: str, from_name: str = "") -> None:
        self.api_key = api_key
        self.from_email = from_email
        self.from_name = from_name or from_email.split("@")[0]
```

The host (`codex_django.messaging.adapters.sendgrid_factory`) reads
`EmailSettings.email_sender_name` and passes it to the factory. Once
the migration lands, no project-specific string ever leaks into the
platform layer.

## Anti-patterns

The following patterns are forbidden in any concrete channel:

1. **Reading config off a global `django.conf.settings`** — channels
   take all config via constructor.
2. **Mutating the input DTO** — `send()` is read-only on the payload.
3. **Holding a long-lived connection in the constructor** — channels
   are created per-worker-startup; if a connection is needed, lazy-init
   it on the first `send()` call. SMTP currently follows this rule via
   `aiosmtplib.send` per call.
4. **Logging the full HTML body or recipient PII** — the
   `BaseDTO.__repr__` masks PII; channels MUST not bypass it.
