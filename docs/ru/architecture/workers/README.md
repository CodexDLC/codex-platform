<!-- type: CONCEPT -->


# Workers (ARQ)

## Назначение

`workers.arq` предоставляет базовую инфраструктуру для ARQ background workers. Стандартизирует конфигурацию воркера, lifecycle-хуки, health probe и интегрируется с механизмом повторов DLQ из Streams.

## Зачем базовый слой

Каждый проект, использующий ARQ, как правило дублирует один и тот же boilerplate: создание Redis pool, написание startup/shutdown хуков, настройка retry, подключение health checks для Docker. Этот модуль предоставляет все эти умолчания один раз.

## Архитектура

```
BaseArqWorkerSettings  (расширить в своём проекте)
   ├── max_jobs = 20
   ├── job_timeout = 60
   ├── max_retries = 5
   ├── on_startup = base_startup    → создаёт /tmp/arq_worker_healthy
   ├── on_shutdown = base_shutdown  → удаляет health-файл
   └── functions = CORE_FUNCTIONS + ваши_задачи

CORE_FUNCTIONS:
   └── requeue_to_stream(ctx, stream_name, payload)
           ├── увеличивает payload._retries
           ├── retries < 5  → XADD обратно в стрим
           └── retries >= 5 → XADD в {stream}:dlq

BaseArqService  (постановка задач из кода приложения / других воркеров)
   └── enqueue_job(function, *args, **kwargs)
```

## Ключевые компоненты

| Компонент | Модуль | Роль |
| :--- | :--- | :--- |
| `BaseArqWorkerSettings` | `base.py` | Базовый `WorkerSettings` — расширить своими функциями |
| `BaseArqService` | `base.py` | Async ARQ клиент для постановки задач |
| `base_startup` | `base.py` | Startup-хук — создаёт health-файл |
| `base_shutdown` | `base.py` | Shutdown-хук — удаляет health-файл |
| `requeue_to_stream` | `base.py` | Базовая функция повтора для Streams DLQ |
| `CORE_FUNCTIONS` | `base.py` | Список встроенных функций, которые должен включать каждый воркер |
| `WorkerConfig` | `config.py` | Pydantic настройки для конфигурации воркера |
| `task_utils` | `task_utils.py` | Хелперы для планирования задач и работы с контекстом |
| `types` | `types.py` | Общие алиасы типов для ARQ контекста и результатов задач |

## Ключевые архитектурные решения

- **Паттерн health-файла** — `/tmp/arq_worker_healthy` создаётся при старте и удаляется при остановке. Docker `HEALTHCHECK` и Kubernetes liveness probe могут делать `test -f` на этот файл.
- **DLQ по соглашению** — имя dead letter queue всегда `{original_stream}:dlq`. Конфигурация не требуется.
- **`CORE_FUNCTIONS` должны быть включены** — при использовании повторов Streams добавьте `CORE_FUNCTIONS` в `functions` вашего воркера. Отсутствие тихо ломает повторы.
- **`BaseArqService` vs адаптер** — `BaseArqService` используется *внутри* воркеров (воркер-воркер постановка). Для постановки со стороны Django/приложения используйте адаптер `delivery/arq.py`.

<!-- TODO: вынести в tasks/using_workers.md -->

## Смотрите также

- [Data Flow →](data_flow.md)
- [Интеграция с повторами Streams →](../streams/README.md)
- [API Reference →](../../../api/workers/arq/index.md)
