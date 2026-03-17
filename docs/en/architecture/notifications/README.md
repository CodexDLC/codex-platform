<!-- type: CONCEPT -->


# Notifications

## Purpose

`notifications` is a multi-channel delivery engine. It decouples message-sending business logic from transport details (SMTP, queue, direct call) and from rendering (Jinja2 templates, plain text).

## Why it's a Service

Sending notifications in distributed systems tends to produce fragile, tightly coupled code. This module solves it through two layers of abstraction:

1. **Transport layer** (`NotificationAdapter`) — decides *how* the payload reaches the worker (ARQ queue, direct call, Django mail).
2. **Delivery layer** (`BaseDeliveryOrchestrator`) — decides *through which channel* the rendered message is actually sent (SMTP, Telegram, SMS), with ordered fallback.

These two concerns are intentionally separate so each can be replaced independently.

## Architecture

```
App code
   │
   ▼
NotificationEngine.send(payload_dto)
   │
   ├── NotificationRenderer   →  renders html/text from template
   │
   └── NotificationAdapter.enqueue()
            │
            ├── ArqAdapter     →  serializes to Redis queue (async)
            └── DirectAdapter  →  calls orchestrator in-process (sync/async)
                                        │
                               BaseDeliveryOrchestrator
                                        │
                               ChannelRegistry.build_channels()
                                        │
                               [channel1, channel2, ...]  (tried in order)
```

## Key Components

| Component | Module | Role |
| :--- | :--- | :--- |
| `NotificationAdapter` | `delivery/base.py` | Protocol — transport contract |
| `ArqDeliveryAdapter` | `delivery/arq.py` | Enqueues to Redis via ARQ |
| `DirectDeliveryAdapter` | `delivery/direct.py` | Runs orchestrator in-process |
| `BaseDeliveryOrchestrator` | `orchestrator.py` | Tries channels in order, stops on first success |
| `ChannelRegistry` | `registry.py` | Builds ordered `DeliveryChannel` list from settings |
| `NotificationRenderer` | `renderer.py` | Renders Jinja2 html/text from `NotificationPayloadDTO` |
| `AsyncEmailClient` | `clients/smtp.py` | SMTP delivery channel |
| `NotificationPayloadDTO` | `dto.py` | Immutable payload contract |

## Key Design Decisions

- **Protocol-based transport** — `NotificationAdapter` is a `Protocol`, not a base class. Swap ARQ for Celery or any queue by implementing two methods.
- **Ordered fallback** — orchestrator tries channels left-to-right; infrastructure exceptions don't stop the chain, they log and continue.
- **Renderer isolation** — template rendering happens before transport. The adapter receives a fully rendered DTO — no Jinja2 in the worker.
- **No magic** — `ChannelRegistry` is explicit: you register channels, you control order.

<!-- TODO: extract to tasks/using_notifications.md -->

## See Also

- [Data Flow →](data_flow.md)
- [API Reference →](../../../api/notifications/index.md)
