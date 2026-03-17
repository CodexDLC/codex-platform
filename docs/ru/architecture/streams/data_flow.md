<!-- type: CONCEPT -->

[← Streams](README.md) | [Главная](../../index.md)

# Data Flow: Streams

## Поток производителя

1. Приложение формирует данные события в виде Python-словаря.
2. `StreamProducer.add_event(event_type, data)` санитизирует payload (все значения → `str`, `None` фильтруются, поле `type` добавляется).
3. Отправляется `XADD {stream_name} * type {event_type} ...поля` в Redis.
4. Redis возвращает ID события (`{timestamp}-{seq}`).

## Поток потребителя

1. При старте `StreamConsumer.ensure_group()` вызывает `XGROUP CREATE` (идемпотентно — пропускает, если группа существует).
2. `StreamConsumer.read(count)` вызывает `XREADGROUP GROUP {group} {consumer} COUNT {count} STREAMS {stream} >`.
3. Каждое сырое сообщение парсится в `StreamEvent(id, event_type, data)`.
4. `StreamDispatcher` передаёт каждое событие в `StreamRouter.dispatch(event)`.
5. `StreamRouter` находит обработчик по `event.event_type` и вызывает его.
6. При успехе → `StreamConsumer.ack(event.id)` → `XACK`.

## Поток повторов / DLQ

```mermaid
sequenceDiagram
    participant Processor
    participant Handler as Обработчик
    participant ARQ as ARQ Worker
    participant Stream as Redis Stream
    participant DLQ

    Processor->>Handler: dispatch(event)
    Handler-->>Processor: бросает исключение

    Processor->>ARQ: enqueue requeue_to_stream(stream, payload)
    ARQ->>ARQ: увеличивает payload._retries

    alt retries < 5
        ARQ->>Stream: XADD (повтор)
    else retries >= 5
        ARQ->>DLQ: XADD {stream}:dlq (с _failed_at, _original_stream)
    end
```

## Полная последовательность

```mermaid
sequenceDiagram
    participant App as Приложение
    participant Producer as StreamProducer
    participant Redis
    participant Consumer as StreamConsumer
    participant Router as StreamRouter
    participant Handler as Обработчик

    App->>Producer: add_event("new_order", {order_id: 1})
    Producer->>Redis: XADD orders * type new_order order_id 1
    Redis-->>Producer: "1700000000-0"

    Consumer->>Redis: XREADGROUP GROUP workers consumer1 STREAMS orders >
    Redis-->>Consumer: [StreamEvent(id, "new_order", {order_id: "1"})]
    Consumer->>Router: dispatch(event)
    Router->>Handler: handle_new_order(event)
    Handler-->>Router: OK
    Consumer->>Redis: XACK orders workers "1700000000-0"
```
