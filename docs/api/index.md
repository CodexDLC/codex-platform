# ⚙️ Technical API Reference

[⬅️ Back](../index.md) | [🏠 Docs Root](../index.md)

This section contains auto-generated technical specifications extracted directly from the source code docstrings. If the code behavior contradicts this documentation, **the code is the bug**.

---

## 📦 Module Map

Select a module to explore its classes, methods, and types:

### 💼 Business Logic
*   **[📅 Booking](./booking/index.md)**: ChainFinder, Scorer, and DTOs for complex scheduling.
*   **[🔢 Calculator](./calculator/index.md)**: Slot calculation and time interval mathematics.
*   **[🤖 LLM Orbit](./llm/index.md)**: Prompt orchestration, Dispatcher, and Router logic.
*   **[📅 Calendar](../en_EN/architecture/calendar/index.md)**: Scheduling integration and time-slot management. *(Note: API docs pending)*

### 📬 Communication & State
*   **[🔌 Redis Service](./redis_service/index.md)**: Key registry, mixins, and optimized caching.
*   **[📬 Notifications](./notifications/index.md)**: Payload builders and notification services.

### 🛡️ Core & Infrastructure
*   **[🛡️ Core](./core/index.md)**: Base DTOs, interfaces, and foundational protocols.
*   **[🔌 Adapters](./adapters/index.md)**: Connectors for Django, Redis, and external services.
*   **[⚙️ Settings](./settings/index.md)**: Pydantic-based configuration management.
*   **[📡 Schemas](./schemas/index.md)**: Data validation and serialization schemas.
*   **[🛠️ Common](./common/index.md)**: Shared utilities (Logger, Phone parsing, Cache, Text).

---

## 🚀 How to Read

1. **Parameters**: All public methods include type hints and descriptions.
2. **Returns**: All return types are specified.
3. **Examples**: Technical code snippets are provided for most public APIs.

---

*Note: This section is generated using `mkdocstrings`.*
