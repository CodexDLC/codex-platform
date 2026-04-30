<!-- type: CONCEPT -->

[← Streams](README.md) | [Home](../../index.md)

# Data Flow: Streams

## Producer Flow

1. App constructs event data as a Python dict.
2. `StreamProducer.publish(event_type, data)` JSON-encodes structured fields, preserves `None`, and injects the `type` field.
3. `XADD {stream_name} * type {event_type} ...fields` is sent to Redis.
4. Redis returns the event ID (`{timestamp}-{seq}`).

## Consumer Flow

1. At startup, `StreamConsumer.ensure_group()` calls `XGROUP CREATE` (idempotent — skips if group exists).
2. `StreamConsumer.read(count)` calls `XREADGROUP GROUP {group} {consumer} COUNT {count} STREAMS {stream} >`.
3. Each raw message is parsed into `StreamEvent(id, event_type, data)`.
4. `StreamProcessor` restores a dispatcher-ready payload with `type`.
5. `StreamDispatcher` looks up matching handler specs and calls enabled handlers.
6. On success → `StreamConsumer.ack(event.id)` → `XACK`.

## Retry / DLQ Flow

```mermaid
sequenceDiagram
    participant Processor
    participant Handler
    participant ARQ as ARQ Worker
    participant Stream as Redis Stream
    participant DLQ

    Processor->>Handler: dispatch(event)
    Handler-->>Processor: raises Exception

    Processor->>ARQ: enqueue requeue_to_stream(stream, payload)
    ARQ->>ARQ: increment payload._retries

    alt retries < 5
        ARQ->>Stream: XADD (retry)
    else retries >= 5
        ARQ->>DLQ: XADD {stream}:dlq (with _failed_at, _original_stream)
    end
```

## Full Sequence

```mermaid
sequenceDiagram
    participant App
    participant Producer as StreamProducer
    participant Redis
    participant Consumer as StreamConsumer
    participant Router as StreamRouter
    participant Handler

    App->>Producer: publish("new_order", {order_id: 1})
    Producer->>Redis: XADD orders * type new_order order_id json:1
    Redis-->>Producer: "1700000000-0"

    Consumer->>Redis: XREADGROUP GROUP workers consumer1 STREAMS orders >
    Redis-->>Consumer: [StreamEvent(id, "new_order", {order_id: 1})]
    Consumer->>Router: dispatch({"type": "new_order", "order_id": 1})
    Router->>Handler: handle_new_order(payload)
    Handler-->>Router: OK
    Consumer->>Redis: XACK orders workers "1700000000-0"
```
