# codex-platform

**Infrastructure, background tasks (ARQ), Redis service, and framework adapters for the Codex WaaS toolkit.**

This library provides the glue between business logic and infrastructure. It includes Redis service wrappers, background task management, and integration adapters for frameworks like Django.

## 🚀 Key Features

*   **Redis Service**: Modern Pydantic-first wrapper for Redis with mixins for strings, hashes, lists, and streams.
*   **ARQ Workers**: Integration with the ARQ background job processor.
*   **Django Adapters**: Seamlessly connect your Django models to the Codex booking engine.
*   **Notifications**: Unified system for sending emails, push notifications, and more using Jinja2 templates.

## 📦 Installation

```bash
pip install "codex-platform[django,redis,arq]"
```

## 🛠️ Quick Start

```python
from codex_tools.redis_service.service import RedisService

redis = RedisService(url="redis://localhost:6379/0")
```

---
*Part of the [Codex WaaS](https://github.com/codexdlc) ecosystem. Requires `codex-core` and `codex-booking`.*
