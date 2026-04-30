# Threading and RFC 5322 Headers

## Why this lives in the platform

Email threading is the only mechanism that reliably keeps a sequence of
inbound and outbound messages stitched together across mail clients
(Gmail collapses, Outlook groups, Apple Mail folds). The Internet
standard for this is RFC 5322's triplet of headers:

* `Message-ID`
* `In-Reply-To`
* `References`

The lily worker already builds these in `_mailbox_headers()`
(`src/workers/notification_worker/tasks/notification_tasks.py:103-113`)
plus a custom `X-Lily-Thread-Key` header. The migration promotes that
helper into the platform — every project (lily, future projects, future
FastAPI hosts) needs the same logic and there is no good reason to
duplicate it.

## `ThreadHeadersDTO` — the canonical shape

```python
class ThreadHeadersDTO(BaseDTO):
    message_id: str
    in_reply_to: str | None = None
    references: list[str] = []
    thread_key: str
    reply_match_token: str | None = None
```

* `message_id`: RFC 5322 `Message-ID` for *this* outgoing message. Host
  generates it (a UUID + the host's domain works fine, e.g.
  `<a8e3b1d2-…@mail.lily.de>`).
* `in_reply_to`: the `Message-ID` of the message we are replying to.
  Empty for compose-new and for the first message of a thread.
* `references`: chronological chain of all `Message-ID`s in this thread,
  ending with `in_reply_to`. Mail clients use this to reconstruct
  threading even when `In-Reply-To` is dropped.
* `thread_key`: opaque, host-issued token that uniquely identifies the
  thread on the host side. Also serialized into the
  `X-Codex-Thread-Key` header so inbound parsers can look up the
  thread without parsing `References`.
* `reply_match_token`: opaque token routed through the `Reply-To`
  header (e.g. `reply+<token>@mail.lily.de`). The inbound webhook /
  IMAP parser uses it to match unstructured replies back to the
  thread. Optional.

## The neutral `X-Codex-Thread-Key` header

The lily codebase currently emits `X-Lily-Thread-Key`. The migration
renames it to `X-Codex-Thread-Key` so that the same header is used
across every codex-* project and inbound parsers can be written once.

| Old header | New header |
|------------|------------|
| `X-Lily-Thread-Key` | `X-Codex-Thread-Key` |

A six-month deprecation: the worker emits **both** headers during the
deprecation window, the inbound parser reads either, and the doc set
flips to recommend the new name immediately. After deprecation the old
header is removed.

## Helpers exposed by `messaging.threading`

```python
def build_message_id(*, domain: str) -> str: ...
def build_thread_key() -> str: ...
def parse_references(header_value: str) -> list[str]: ...
def serialize_references(message_ids: list[str]) -> str: ...
def render_email_headers(dto: ThreadHeadersDTO) -> dict[str, str]: ...
```

* `build_message_id("mail.lily.de") -> "<a8e3b1d2-…@mail.lily.de>"` —
  uses `uuid.uuid4()`.
* `build_thread_key() -> "tk_<urlsafe-base64-of-uuid4>"` — what the
  lily `Message.thread_key` field currently stores.
* `parse_references` / `serialize_references` are the inverse pair the
  inbound transport uses when associating a reply with a thread.
* `render_email_headers` returns the dict that an SMTP / SendGrid
  channel emits as headers.

The helpers are deliberately stateless — they do not read DB, cache, or
request context. They are pure transformations from a DTO to a header
dict and back.

## How channels use the headers

The `DeliveryChannel.send` signature gains an optional kwarg:

```python
async def send(
    self,
    to: str,
    subject: str,
    html_content: str | None,
    text_content: str | None,
    headers: ThreadHeadersDTO | None = None,
) -> bool: ...
```

* `AsyncEmailClient` (SMTP) calls `render_email_headers(headers)` and
  attaches the result to the `EmailMessage` before send.
* `SendGridChannel` (HTTP) maps the same dict to SendGrid's
  `personalizations[0].headers` field.
* SMS / Telegram / WhatsApp channels ignore the field.

When `headers is None` no thread-related header is emitted. The lily
booking lifecycle uses this — booking confirmations are not part of a
conversation thread.

## Inbound transport (out of scope, but designed for)

Although the inbound transport is deferred (we currently rely on
SendGrid Inbound Parse / IMAP via the existing email-import service),
the `ThreadHeadersDTO` schema is designed to support it without
revisiting:

* On inbound, the parser reads `References`, `In-Reply-To`, and
  `X-Codex-Thread-Key`.
* If `X-Codex-Thread-Key` is present, the parser fetches the thread
  directly. Otherwise it falls back to scanning `References` for known
  `Message-ID`s.
* If neither matches, the message is treated as a new thread; the
  parser issues a fresh `thread_key`.

The lily `email_import.py` already implements this logic; the docs
codify it as the canonical recipe.

## Anti-patterns

* **Generating `Message-ID` on the worker side.** The host owns the
  message identity; the worker is a delivery transport. Workers that
  generate `Message-ID` make it impossible to record the ID before
  send, which breaks audit and inbound matching.
* **Storing `Message-ID` in the database without angle brackets.** RFC
  5322 requires the brackets; tools like `email.policy.default` will
  add or strip them inconsistently. Store and compare with brackets.
* **Reusing a `Message-ID` for retries.** Each retry emits a *new*
  `Message-ID`. The original one remains in the audit log so the
  recipient sees one or the other but not both as duplicates of the
  same identity.
