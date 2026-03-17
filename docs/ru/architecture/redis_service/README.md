<!-- type: CONCEPT -->


# Redis Service

## Назначение

`redis_service` — типизированная async-абстракция над `redis-py`. Заменяет сырые вызовы `await client.hset(...)` структурированными, безопасными классами операций и системой шаблонов ключей.

## Зачем это сервис

Прямое использование `redis-py` рассеивает строки ключей по всему коду и не даёт единообразной обработки ошибок. Модуль решает две проблемы:

1. **Безопасность ключей** — шаблоны `BaseRedisKey` проверяют структуру ключа при создании. Опечатки в префиксах ключей становятся ошибками типов.
2. **Изоляция ошибок** — каждая операция оборачивает Redis-вызовы в типизированные исключения (`RedisConnectionError`, `RedisServiceError`). Вызывающий код точно знает, что может упасть и почему.

## Архитектура

```
RedisService (корень композиции)
   ├── hash        → HashOperations
   ├── string      → StringOperations
   ├── list        → ListOperations
   ├── set         → SetOperations
   ├── zset        → ZSetOperations
   ├── json        → JsonStringOperations   (обычный Redis, без модулей)
   ├── json_module → JsonModuleOperations   (требует серверный модуль RedisJSON)
   └── pipeline    → PipelineOperations

Все операции получают один и тот же redis.asyncio.Redis клиент.
Селективная композиция: используйте классы Operations напрямую, если не нужны все типы.
```

## Ключевые компоненты

| Компонент | Модуль | Роль |
| :--- | :--- | :--- |
| `RedisService` | `service.py` | Полный корень композиции — все операции в одном объекте |
| `BaseRedisKey` | `keys.py` | Базовый класс для шаблонов ключей |
| `HashOperations` | `operations/hash.py` | HSET / HGET / HGETALL / HDEL |
| `StringOperations` | `operations/string.py` | SET / GET / DELETE с TTL |
| `ListOperations` | `operations/list_.py` | LPUSH / RPUSH / LRANGE / LTRIM |
| `SetOperations` | `operations/set_.py` | SADD / SMEMBERS / SREM / SISMEMBER |
| `ZSetOperations` | `operations/zset.py` | ZADD / ZRANGE / ZRANGEBYSCORE / ZREM |
| `JsonStringOperations` | `operations/json_string.py` | JSON через SET/GET + json.dumps/loads, работает с любым Redis |
| `JsonModuleOperations` | `operations/json_module.py` | JSON.SET / JSON.GET через серверный модуль RedisJSON |
| `PipelineOperations` | `operations/pipeline.py` | Атомарные пакеты из нескольких команд |
| `BaseManager` | `managers/base_manager.py` | Базовый класс высокоуровневых доменных менеджеров |

## Ключевые архитектурные решения

- **Композиция вместо наследования** — `RedisService` компонует операции, а не наследует их. Используйте операции напрямую для селективной композиции.
- **Типизированные исключения** — `RedisConnectionError` для сетевых сбоев, `RedisServiceError` для остальных ошибок Redis. Сырые `redis.exceptions.*` никогда не пробрасываются вызывающему.
- **Без управления соединением** — модуль принимает уже созданный `redis.asyncio.Redis` клиент. Жизненный цикл (connect/disconnect) — ответственность вызывающего.
- **Два подхода к JSON** — `JsonStringOperations` (через `service.json`) работает с любым Redis: сериализует через `json.dumps/loads`. `JsonModuleOperations` (через `service.json_module`) использует серверный модуль RedisJSON для работы с вложенными путями и атомарных обновлений.

<!-- TODO: вынести в tasks/using_redis_service.md -->

## Смотрите также

- [Data Flow →](data_flow.md)
- [API Reference →](../../../api/redis_service/index.md)
