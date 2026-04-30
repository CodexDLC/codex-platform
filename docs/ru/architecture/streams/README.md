<!-- type: CONCEPT -->


# Streams (Потоки)

## Назначение

`streams` — шина событий на основе Redis Streams (XADD/XREADGROUP). Обеспечивает доставку «как минимум один раз» через consumer groups, логические группы обработчиков для разделения монолита на сервисы, автоматический повтор через ARQ и Dead Letter Queue (DLQ) для постоянно падающих событий.

## Почему Redis Streams

В отличие от pub/sub (fire-and-forget) или обычных Redis-списков, Redis Streams обеспечивают:

- **Consumer groups** — несколько консьюмеров могут читать из одного стрима без дублирования работы.
- **Постоянная история** — события не теряются при временной недоступности консьюмера.
- **ACK-семантика** — сообщение остаётся в Pending Entries List (PEL) до явного подтверждения, предотвращая тихую потерю.

## Архитектура

```
Сторона производителя              Сторона потребителя
──────────────────────             ──────────────────────────────────
App → StreamProducer               StreamConsumer (XREADGROUP)
         │                               │
         │ XADD                          ▼
         ▼                         StreamEvent
      Redis Stream ───────────────► StreamDispatcher
                                         │
                                   StreamRouter.dispatch()
                                         │
                               ┌─────────┴──────────┐
                               ▼                    ▼
                          handler_A()          handler_B()
                               │
                               ▼
                          StreamConsumer.ack()  ← XACK при успехе
                               │
                        При ошибке: ARQ requeue_to_stream
                               │ (до 5 попыток)
                               ▼
                            stream:dlq  ← Dead Letter Queue
```

## Ключевые компоненты

| Компонент | Модуль | Роль |
| :--- | :--- | :--- |
| `StreamProducer` | `producer.py` | Записывает события через XADD и предоставляет базовый request/reply |
| `StreamConsumer` | `consumer.py` | Читает через XREADGROUP, подтверждает через XACK |
| `StreamEvent` | `consumer.py` | Распарсенный dataclass события (`id`, `event_type`, `data`) |
| `StreamDispatcher` | `dispatcher.py` | Запускает цикл потребления, диспатчит в роутер |
| `StreamProcessor` | `processor.py` | Оборачивает dispatch + ACK + логику повторов |
| `StreamRouter` | `router.py` | Маппит `event_type` → функция-обработчик |
| `StreamRuntime` | `runtime.py` | Собирает producer, consumer, dispatcher, processor и выбранные логические группы |

## Ключевые архитектурные решения

- **Consumer groups обязательны** — модуль использует исключительно `XREADGROUP`. Одиночный `XREAD` не поддерживается. Создавайте группу через `StreamConsumer.ensure_group()` при старте.
- **Логические группы — это metadata обработчиков** — `@router.on(..., group="actor_state")` помечает handler для выбора в runtime; Redis-доставка по-прежнему управляется `consumer_group`.
- **Монолит по умолчанию** — `StreamRuntimeConfig(enabled_groups=None)` включает все handlers в одном процессе.
- **Режим отдельного сервиса** — задайте `enabled_groups={"actor_state"}` и non-monolith Redis `consumer_group`, чтобы сервис получал собственное представление stream.
- **JSON-safe payloads** — структурные значения кодируются JSON-prefixed stream fields и декодируются обратно в Python-значения при чтении.
- **Базовый request/reply** — `StreamProducer.request()` публикует событие с `correlation_id` и ждет ответ в `reply:{correlation_id}`.
- **Повтор через ARQ** — упавшие события ставятся обратно в исходный стрим через задачу ARQ `requeue_to_stream` (часть `workers.arq.CORE_FUNCTIONS`). После 5 попыток → DLQ (`{stream}:dlq`).
- **ACK только после успеха** — XACK вызывается только после успешного завершения обработчика без исключений. Инфраструктурные исключения пробрасываются в процессор для планирования повтора.

<!-- TODO: вынести в tasks/using_streams.md -->

## Смотрите также

- [Data Flow →](data_flow.md)
- [API Reference →](../../../api/streams/index.md)
