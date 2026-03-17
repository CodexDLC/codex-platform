<!-- type: CONCEPT -->


# Workers (ARQ)

## Purpose

`workers.arq` provides base infrastructure for ARQ background workers. It standardizes worker configuration, lifecycle hooks, health probes, and integrates with the Streams DLQ retry mechanism.

## Why a Base Layer

Each project using ARQ tends to duplicate the same boilerplate: creating a Redis pool, writing startup/shutdown hooks, configuring retries, and wiring health checks for Docker. This module provides those defaults once.

## Architecture

```
BaseArqWorkerSettings  (extend in your project)
   ├── max_jobs = 20
   ├── job_timeout = 60
   ├── max_retries = 5
   ├── on_startup = base_startup    → touches /tmp/arq_worker_healthy
   ├── on_shutdown = base_shutdown  → removes health file
   └── functions = CORE_FUNCTIONS + your_tasks

CORE_FUNCTIONS:
   └── requeue_to_stream(ctx, stream_name, payload)
           ├── increments payload._retries
           ├── retries < 5  → XADD back to stream
           └── retries >= 5 → XADD to {stream}:dlq

BaseArqService  (enqueue from application code / other workers)
   └── enqueue_job(function, *args, **kwargs)
```

## Key Components

| Component | Module | Role |
| :--- | :--- | :--- |
| `BaseArqWorkerSettings` | `base.py` | Base `WorkerSettings` class — extend with your functions |
| `BaseArqService` | `base.py` | Async ARQ client for enqueueing jobs |
| `base_startup` | `base.py` | Startup hook — creates health file |
| `base_shutdown` | `base.py` | Shutdown hook — removes health file |
| `requeue_to_stream` | `base.py` | Core retry function for Streams DLQ |
| `CORE_FUNCTIONS` | `base.py` | List of built-in functions every worker should include |
| `WorkerConfig` | `config.py` | Pydantic settings for worker configuration |
| `task_utils` | `task_utils.py` | Helpers for task scheduling and context |
| `types` | `types.py` | Shared type aliases for ARQ context and job results |

## Key Design Decisions

- **Health file pattern** — `/tmp/arq_worker_healthy` is created on startup and removed on shutdown. Docker `HEALTHCHECK` and Kubernetes liveness probes can `test -f` this file.
- **DLQ by convention** — the dead letter queue name is always `{original_stream}:dlq`. No configuration needed.
- **`CORE_FUNCTIONS` must be included** — if using Streams retry, add `CORE_FUNCTIONS` to your worker's `functions` list. Missing it silently breaks retry.
- **`BaseArqService` vs adapter** — `BaseArqService` is for use *inside* workers (worker-to-worker enqueueing). For Django/app-side enqueueing, use `delivery/arq.py` adapter.

<!-- TODO: extract to tasks/using_workers.md -->

## See Also

- [Data Flow →](data_flow.md)
- [Streams retry integration →](../streams/README.md)
- [API Reference →](../../../api/workers/arq/index.md)
