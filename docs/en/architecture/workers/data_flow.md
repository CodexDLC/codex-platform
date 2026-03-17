<!-- type: CONCEPT -->

[← Workers](README.md) | [Home](../../index.md)

# Data Flow: Workers (ARQ)

## Job Lifecycle

1. **Enqueue** — application code (or another worker) calls `BaseArqService.enqueue_job(function_name, *args)`. The job is written to Redis.

2. **Pick up** — ARQ worker polls Redis and dequeues the job for a registered function.

3. **Execute** — the task function runs with the ARQ `ctx` dict injected as first argument. `ctx` contains the Redis pool and any objects registered in `on_startup`.

4. **Success** — ARQ marks the job result as complete and optionally stores it for `keep_result` seconds.

5. **Failure** — ARQ retries the job up to `max_retries` times with `retry_delay` seconds between attempts. After `max_retries` exhausted, the job is marked as failed.

## Sequence Diagram

```mermaid
sequenceDiagram
    participant App
    participant Service as BaseArqService
    participant Redis
    participant Worker as ARQ Worker
    participant Task

    App->>Service: enqueue_job("send_email", payload)
    Service->>Redis: RPUSH arq:queue job_data
    Redis-->>Service: job_id

    Worker->>Redis: BLPOP arq:queue
    Redis-->>Worker: job_data
    Worker->>Task: send_email(ctx, payload)
    Task-->>Worker: result

    alt success
        Worker->>Redis: SET arq:result:{job_id} result
    else failure (retries left)
        Worker->>Redis: RPUSH arq:queue job_data (retry_count++)
    else max retries exhausted
        Worker->>Redis: SET arq:result:{job_id} JobStatus.failed
    end
```

## Startup / Shutdown

```mermaid
sequenceDiagram
    participant Docker
    participant Worker as ARQ Worker
    participant FS as /tmp filesystem

    Docker->>Worker: start process
    Worker->>Worker: on_startup(ctx)
    Worker->>FS: touch /tmp/arq_worker_healthy
    Note over Docker,FS: HEALTHCHECK: test -f /tmp/arq_worker_healthy

    Docker->>Worker: SIGTERM
    Worker->>Worker: on_shutdown(ctx)
    Worker->>FS: unlink /tmp/arq_worker_healthy
```

## Streams Retry Integration

When a Streams handler fails, the `StreamProcessor` enqueues `requeue_to_stream` as an ARQ job. This function increments `_retries` on the payload and re-inserts it into the original stream (or DLQ after 5 retries).

See [Streams Data Flow](../streams/data_flow.md) for the full retry sequence.
