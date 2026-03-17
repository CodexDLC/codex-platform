# 🤖 AI Assistant Navigation Map (codex-tools)

This document is a "cheat sheet" for AI agents (like yourself) to help you navigate the `codex-tools` library and its documentation. Use this to understand the architecture, coding standards, and where to find specific technical details.

---

## 🧠 Mental Model: "Lego for WaaS"

`codex-tools` is NOT a monolithic application. It is a set of **independent, high-performance bricks** for building Booking and Scheduling systems (WaaS - Workspace as a Service).

1.  **Resources & Services**: Everything is a Resource (Staff, Room, Tool) providing a Service (Haircut, Consultation).
2.  **Time Grids**: Availability is calculated in memory using bitwise-like logic or interval math, not raw DB queries.
3.  **Ports & Adapters**: The core logic is pure Python. All external dependencies (Django, Redis, ARQ) are isolated via Adapters.

---

## 🗺️ Documentation Landscape

| Goal | Path | Description |
|:---|:---|:---|
| **Understand "Why"** | [docs/ru_RU/index.md](./ru_RU/index.md) | Architect's Mind & Philosophy (Russian). |
| **Understand "How"** | [docs/en_EN/index.md](./en_EN/index.md) | Conceptual & Integration flows (English). |
| **Technical Specs** | [docs/api/index.md](./api/index.md) | Auto-generated technical truth (Docstrings). |
| **Central Hub** | [docs/index.md](./index.md) | Entry point for all documentation. |

---

## 🔍 Quest-to-Path Mapping

### 1. 🏛️ Core Architecture & Logic
*   **"How does Booking work?"**
    *   Concept: [docs/en_EN/architecture/booking/index.md](./en_EN/architecture/booking/index.md)
    *   Technical: [docs/api/booking/index.md](./api/booking/index.md)
*   **"How to use LLM Orbit?"**
    *   Concept: [docs/en_EN/architecture/llm/index.md](./en_EN/architecture/llm/index.md)
    *   Technical: [docs/api/llm/index.md](./api/llm/index.md)
*   **"How to implement a new Adapter?"**
    *   Concept: [docs/en_EN/architecture/adapters/index.md](./en_EN/architecture/adapters/index.md)
    *   Protocols: [docs/api/core/interfaces.md](./api/core/interfaces.md)

### 2. 🔌 Infrastructure & State
*   **"Manage Redis Keys"**
    *   Concept: [docs/en_EN/architecture/redis_service/index.md](./en_EN/architecture/redis_service/index.md)
    *   Technical: [docs/api/redis_service/index.md](./api/redis_service/index.md)
*   **"Configure Settings"**
    *   Concept: [docs/en_EN/architecture/settings/index.md](./en_EN/architecture/settings/index.md)
    *   Technical: [docs/api/settings/index.md](./api/settings/index.md)

---

## 💻 Quick Code Context (WIP)
*This section will be populated with ideal code snippets as we refine each module.*

- **Booking**: `[TODO: Add ChainFinder example]`
- **LLM Orbit**: `[TODO: Add Dispatcher example]`
- **Redis**: `[TODO: Add BaseRedisKey example]`

---

## 🛡️ Core Directives for AI

1.  **Framework Agnosticism**: Never suggest putting database logic into `src/codex_tools`. Use **Adapters**.
2.  **Immutability First**: All DTOs are `frozen=True`. Use `.model_copy(update=...)` for changes.
3.  **PII Responsibility**: Mask personal data in logs. Use `codex_tools.core.pii` for registry.
4.  **No Magic Strings**: For Redis, always suggest using `BaseRedisKey` subclasses.
5.  **Domain Neutrality**: Use "Resources" and "Services" instead of "Masters" or "Salons".

---

## 🚫 Anti-Patterns
*   **DON'T** import `django.*` or `fastapi.*` inside `core/` or `booking/`.
*   **DON'T** use raw `f-strings` for Redis keys.
*   **DON'T** perform I/O (DB/API) inside `ChainFinder` or `Scorer`.

---

*Tip: If you are lost, start from [docs/index.md](./index.md) — it is the central hub.*
