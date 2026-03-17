<!-- type: CONCEPT -->


# Notifications (Уведомления)

## Назначение

`notifications` — многоканальный движок доставки сообщений. Разделяет бизнес-логику отправки от транспорта (SMTP, очередь, прямой вызов) и от рендеринга (Jinja2 шаблоны, plain text).

## Зачем это сервис

В распределённых системах отправка уведомлений порождает хрупкий, сильно связанный код. Модуль решает это через два уровня абстракции:

1. **Транспортный уровень** (`NotificationAdapter`) — определяет *как* полезная нагрузка попадает к воркеру (ARQ-очередь, прямой вызов, Django mail).
2. **Уровень доставки** (`BaseDeliveryOrchestrator`) — определяет *через какой канал* отрендеренное сообщение фактически отправляется (SMTP, Telegram, SMS) с последовательным fallback.

Эти два слоя разделены намеренно — каждый можно заменить независимо.

## Архитектура

```
Код приложения
   │
   ▼
NotificationEngine.send(payload_dto)
   │
   ├── NotificationRenderer   →  рендерит html/text из шаблона
   │
   └── NotificationAdapter.enqueue()
            │
            ├── ArqAdapter     →  сериализует в Redis-очередь (async)
            └── DirectAdapter  →  вызывает оркестратор в процессе (sync/async)
                                        │
                               BaseDeliveryOrchestrator
                                        │
                               ChannelRegistry.build_channels()
                                        │
                               [channel1, channel2, ...]  (перебор по порядку)
```

## Ключевые компоненты

| Компонент | Модуль | Роль |
| :--- | :--- | :--- |
| `NotificationAdapter` | `delivery/base.py` | Protocol — контракт транспорта |
| `ArqDeliveryAdapter` | `delivery/arq.py` | Ставит в очередь Redis через ARQ |
| `DirectDeliveryAdapter` | `delivery/direct.py` | Запускает оркестратор в процессе |
| `BaseDeliveryOrchestrator` | `orchestrator.py` | Перебирает каналы, останавливается на первом успехе |
| `ChannelRegistry` | `registry.py` | Собирает упорядоченный список `DeliveryChannel` из настроек |
| `NotificationRenderer` | `renderer.py` | Рендерит Jinja2 html/text из `NotificationPayloadDTO` |
| `AsyncEmailClient` | `clients/smtp.py` | SMTP-канал доставки |
| `NotificationPayloadDTO` | `dto.py` | Иммутабельный контракт полезной нагрузки |

## Ключевые архитектурные решения

- **Protocol-based транспорт** — `NotificationAdapter` это `Protocol`, не базовый класс. Замените ARQ на Celery или любую очередь, реализовав два метода.
- **Упорядоченный fallback** — оркестратор перебирает каналы слева направо; инфраструктурные исключения не останавливают цепочку, а логируются и продолжают.
- **Изоляция рендерера** — рендеринг шаблонов происходит до транспорта. Адаптер получает полностью отрендеренный DTO — никакого Jinja2 в воркере.
- **Без магии** — `ChannelRegistry` явный: вы регистрируете каналы, вы контролируете порядок.

<!-- TODO: вынести в tasks/using_notifications.md -->

## Смотрите также

- [Data Flow →](data_flow.md)
- [API Reference →](../../../api/notifications/index.md)
