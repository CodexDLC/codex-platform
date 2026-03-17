<!-- type: CONCEPT -->


# Streams

## Purpose

`streams` is an event bus built on Redis Streams (XADD/XREADGROUP). It provides at-least-once delivery with consumer groups, automatic retry via ARQ, and a Dead Letter Queue (DLQ) for permanently failed events.

## Why Redis Streams

Unlike pub/sub (fire-and-forget) or simple Redis lists, Redis Streams provide:

- **Consumer groups** — multiple consumers can process from the same stream without duplicating work.
- **Persistent history** — events are not lost if the consumer is temporarily down.
- **ACK semantics** — a message stays in the Pending Entries List (PEL) until explicitly acknowledged, preventing silent loss.

## Architecture

```
Producer side                     Consumer side
─────────────────────             ──────────────────────────────────
App → StreamProducer              StreamConsumer (XREADGROUP)
         │                               │
         │ XADD                          ▼
         ▼                         StreamEvent
      Redis Stream ─────────────► StreamDispatcher
                                         │
                                   StreamRouter.dispatch()
                                         │
                               ┌─────────┴──────────┐
                               ▼                    ▼
                          handler_A()          handler_B()
                               │
                               ▼
                          StreamConsumer.ack()  ← XACK on success
                               │
                        On failure: ARQ requeue_to_stream
                               │ (up to 5 retries)
                               ▼
                            stream:dlq  ← Dead Letter Queue
```

## Key Components

| Component | Module | Role |
| :--- | :--- | :--- |
| `StreamProducer` | `producer.py` | Writes events via XADD, sanitizes payload to `str` |
| `StreamConsumer` | `consumer.py` | Reads via XREADGROUP, acknowledges via XACK |
| `StreamEvent` | `consumer.py` | Parsed event dataclass (`id`, `event_type`, `data`) |
| `StreamDispatcher` | `dispatcher.py` | Runs the consume loop, dispatches to router |
| `StreamProcessor` | `processor.py` | Wraps dispatch + ACK + retry logic |
| `StreamRouter` | `router.py` | Maps `event_type` → handler function |

## Key Design Decisions

- **Consumer groups required** — the module uses `XREADGROUP` exclusively. Single-consumer `XREAD` is not supported. Create the group via `StreamConsumer.ensure_group()` at startup.
- **Sanitized payloads** — `StreamProducer._sanitize()` converts all values to `str` and drops `None`. Redis Streams only store string fields.
- **Retry via ARQ** — failed events are requeued to the original stream with `_retries` counter via the `requeue_to_stream` ARQ task (part of `workers.arq.CORE_FUNCTIONS`). After 5 retries → DLQ (`{stream}:dlq`).
- **ACK after success only** — XACK is called only after the handler completes without raising. Infrastructure exceptions propagate to the processor for retry scheduling.

<!-- TODO: extract to tasks/using_streams.md -->

## See Also

- [Data Flow →](data_flow.md)
- [API Reference →](../../../api/streams/index.md)
