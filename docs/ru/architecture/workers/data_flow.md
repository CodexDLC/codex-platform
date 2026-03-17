<!-- type: CONCEPT -->

[← Workers](README.md) | [Главная](../../index.md)

# Data Flow: Workers (ARQ)

## Жизненный цикл задачи

1. **Постановка в очередь** — код приложения (или другой воркер) вызывает `BaseArqService.enqueue_job(function_name, *args)`. Задача записывается в Redis.

2. **Извлечение** — ARQ-воркер опрашивает Redis и извлекает задачу для зарегистрированной функции.

3. **Выполнение** — функция-задача запускается с ARQ `ctx`-словарём, инжектированным первым аргументом. `ctx` содержит Redis pool и все объекты, зарегистрированные в `on_startup`.

4. **Успех** — ARQ помечает результат задачи как выполненный и опционально хранит его `keep_result` секунд.

5. **Ошибка** — ARQ повторяет задачу до `max_retries` раз с паузой `retry_delay` секунд между попытками. После исчерпания `max_retries` задача помечается как упавшая.

## Диаграмма последовательности

```mermaid
sequenceDiagram
    participant App as Приложение
    participant Service as BaseArqService
    participant Redis
    participant Worker as ARQ Worker
    participant Task as Задача

    App->>Service: enqueue_job("send_email", payload)
    Service->>Redis: RPUSH arq:queue job_data
    Redis-->>Service: job_id

    Worker->>Redis: BLPOP arq:queue
    Redis-->>Worker: job_data
    Worker->>Task: send_email(ctx, payload)
    Task-->>Worker: result

    alt успех
        Worker->>Redis: SET arq:result:{job_id} result
    else ошибка (остались попытки)
        Worker->>Redis: RPUSH arq:queue job_data (retry_count++)
    else попытки исчерпаны
        Worker->>Redis: SET arq:result:{job_id} JobStatus.failed
    end
```

## Startup / Shutdown

```mermaid
sequenceDiagram
    participant Docker
    participant Worker as ARQ Worker
    participant FS as /tmp filesystem

    Docker->>Worker: запуск процесса
    Worker->>Worker: on_startup(ctx)
    Worker->>FS: touch /tmp/arq_worker_healthy
    Note over Docker,FS: HEALTHCHECK: test -f /tmp/arq_worker_healthy

    Docker->>Worker: SIGTERM
    Worker->>Worker: on_shutdown(ctx)
    Worker->>FS: unlink /tmp/arq_worker_healthy
```

## Интеграция с повторами Streams

Когда обработчик Streams падает, `StreamProcessor` ставит в очередь `requeue_to_stream` как ARQ-задачу. Эта функция увеличивает `_retries` в payload и повторно вставляет событие в исходный стрим (или в DLQ после 5 попыток).

Полная последовательность повторов — в [Streams Data Flow](../streams/data_flow.md).
