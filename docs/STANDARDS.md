# Стандарты документации проекта Codex Tools

## 1. 📂 Общая структура разделов (Domain-Driven Structure)
Мы делим документацию не по файлам кода, а по **Назначению (Domain/Service)**, чтобы структура была готова к превращению в монорепо или набор отдельных библиотек.

| Раздел (RU/EN) | Описание | Состав (примеры) |
| :--- | :--- | :--- |
| architecture/domains/ | Чистая бизнес-логика (Ядро) | booking, calculator, calendar |
| architecture/services/ | Инфраструктурные сервисы | llm, notifications, worker, redis |
| architecture/platform/ | Базовые утилиты и конфиги | common, core, settings, schemas |
| architecture/adapters/ | Мосты к фреймворкам | django, arq |

---

## 2. 🛠 API Reference (docs/api/) — Зеркало кода
Здесь используются Markdown-файлы на каждый ключевой Python-модуль. Структура в `docs/api/` должна полностью повторять путь в `src/`.

- **Иерархия:** Если в коде есть `src/codex_tools/booking/chain_finder.py`, то в API будет `docs/api/booking/chain_finder.md`.
- **Группировка:** В меню MkDocs это выглядит как: `API Reference -> booking -> chain_finder`.
- **Наполнение:** Каждый файл содержит директиву `::: codex_tools.module_name`, которая автоматически вытягивает классы и функции из кода.

---

## 3. 🗺 Architecture Guides — Зеркало логики
Здесь мы описываем **Домен целиком**, чтобы была видна общая картина взаимодействия.

Внутри `architecture/domains/` (или `services/`):
- **Папка на Домен:** Создаем подпапку для каждого крупного узла (например, `architecture/domains/booking/`).
- **Файлы внутри:**
    - `README.md` — Входная точка: общая схема, назначение домена, быстрый старт.
    - `logic_deep_dive.md` — (Опционально) Детальное описание сложных алгоритмов (например, `ChainFinder`).
    - `data_flow.md` — Схема прохождения данных (от DTO до ответа).

---

## 4. 🧭 Обновленный маппинг (Пример)

| Тип контента | Путь в коде | Путь в Docs (RU/EN) | Стиль изложения |
| :--- | :--- | :--- | :--- |
| **API** | `booking/dto.py` | `docs/api/booking/dto.md` | Справочник: поля, типы, валидация. |
| **API** | `booking/chain_finder.py` | `docs/api/booking/chain_finder.md` | Справочник: аргументы методов, возвращаемые значения. |
| **Архитектура** | `booking/` | `docs/[lang]/architecture/domains/booking/README.md` | Гайд: как использовать эти DTO и Finder вместе. |

---

## 5. 🚀 Evolution (Roadmap & Tasks)
Для управления развитием проекта используется папка `docs/evolution/`. Она идентична в RU и EN версиях.

- **Roadmap:** `docs/evolution/roadmap.md` — Глобальный план развития.
- **Tasks:** `docs/evolution/tasks/[domain_name]/[task_name].md` — Конкретные задачи.
- **Связь с архитектурой:** Каждая задача должна ссылаться на текущую архитектуру или API, которые она меняет.
    - *Пример:* `Affected API: [api/llm/protocol.md](../../../api/llm/protocol.md)`.

---

## 6. ☯️ Правило Зеркальности (Strict Mirroring)
RU и EN папки должны быть структурно идентичны.
Если в `docs/en_EN/architecture/domains/booking.md` добавлена новая схема — она обязана появиться в `docs/ru_RU/...`.
Технические детали (типы, аргументы) не копируются, а указываются ссылкой на **API Reference**.

---

## 7. 🧭 Навигационный стандарт (Breadcrumbs)
В начале каждого файла обязательна навигация для удобства перемещения:

```markdown
[⬅️ Назад к разделу](../README.md) | [🗺 Roadmap](../../evolution/roadmap.md) | [🏠 Главная](../../../README.md)
```
