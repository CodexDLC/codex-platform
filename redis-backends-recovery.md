# Plan: Fix codex_django Redis backends — client factory + sync/async split + feature flag rollout

> [!NOTE]
> **Project Focus:** This repository (**codex-platform**) is responsible for **Track A**.
> The full plan is included below to maintain context and avoid narrowing down data.

## Context

Production `lily_website` ловил пять Redis-багов:

1. **`AttributeError: 'DashboardRedisManager' object has no attribute '_client'`** на `GET /ru/cabinet/` — главный блокер.
2. `RuntimeError: Event loop is closed` — admin login → `SessionStore.asave`.
3. `RuntimeError: got Future attached to a different loop` — повторные `FixtureHashManager.get_hash/set_hash`.
4. `redis.exceptions.DataError: Invalid input of type 'bool'` — `update_site_settings` / `update_all_content`.
5. `Error fetching static page SEO for key team/contacts: Event loop is closed` — `codex_django.core.seo.selectors.get_static_page_seo`.

Плюс infra-инцидент: `The "ATTV6fkq" variable is not set` — `$` в Redis-пароле, docker-compose интерполирует. Надо проверить.

Prod hotfix'ом (`951a6c4`) переведён на `django_redis` + `sessions.backends.db`, entrypoint очищен. Цель — починить codex_django Redis engine и вернуть его через **feature flag** с возможностью отката.

## Root causes

1. **Несогласованный контракт менеджеров.** `BaseRedisManager` (codex-platform) и `BaseDjangoRedisManager` не присваивают `self._client`. `DashboardRedisManager` и SEO selector используют `self._client.*`, которого нет.
2. **Живой async client переживает свой event loop.** `Redis.from_url(...)` создаётся один раз в `__init__`, `async_to_sync` создаёт новый loop на каждый sync-вызов — клиент держит Future'ы мёртвого loop.
3. **Module-level instantiation** (`_manager = DashboardRedisManager()` в `cabinet/selector/dashboard.py:41`, аналогично в SEO).
4. **CacheCoder не подключён в HSET-пути.** `DjangoSiteSettingsManager.asave_instance` (`core/redis/managers/settings.py:95-106`) пишет сырой `instance.to_dict()`. CacheCoder покрывает datetime/Decimal/UUID/bytes/set, но не bool/None/Enum/Path/Promise. В `lily_website/src/lily_backend/system/models/settings.py:89-98` дублирующий костыль.
5. **Sync Django path завязан на async_to_sync** для cache/session/dashboard/SEO. Нужен отдельный sync-путь поверх `redis.Redis`.

## Глобальные принципы (жёсткие)

Библиотеки в alpha, consumer один — делаем чистый breaking change, compat-слой не тащим.

- **Единственный публичный API менеджеров — 4 context manager'а**: `sync_string()`, `sync_hash()`, `async_string()`, `async_hash()`. Всё старое (`self._client`, `self.string`, `self.hash` как атрибуты) — **удаляется**, не заменяется alias'ом.
- **Sync code → sync_* методы → `redis.Redis`**. `async_to_sync` из sync Django hot paths запрещён.
- **Async code → async_* методы → `redis.asyncio.Redis`**.
- **Менеджер принимает `client_factory: Callable[[], Redis]`, а НЕ live client**. Default factory читает `settings.REDIS_URL`. Live client между вызовами не хранится.
- **New client per operation с `aclose()` / `close()` в `finally`** (Variant A). Pool / loop-local cache — follow-up при превышении p95-бюджета.
- **Grep-gate** (обязательная часть CI / ручной проверки перед мержем):
  ```
  rg "self\._client|\.string\.|\.hash\." src/codex_django src/codex_platform src/lily_backend
  ```
  Все находки либо удалены, либо явно внутри operation-классов codex-platform. Новый код с `self._client` / атрибутным доступом к `.string`/`.hash` не мержится.
- **Rollout через feature flag** `USE_CODEX_REDIS_BACKENDS`; `django-redis` оставляем в deps как fallback.
- **CacheCoder без маркеров**: `None→""`, `bool→"1"/"0"`, `Enum→CacheCoder.dump(value.value)`. Typed restore делает `DjangoSiteSettingsManager` на основе Django field types.

## Треки (независимо разрабатываемые)

Ветка в каждом репо: `codex/fix-redis-backends`. Треки разделены так, чтобы A/B/C/D можно было вести параллельно разными исполнителями; E/F/G — ниже по зависимостям.

---

### Трек A — codex-platform: sync operations + encoder hook (без alias)

**Репо:** `C:\install\projects\codex_tools\codex-platform`

`BaseRedisManager` остаётся как есть для async service layer; он **не используется** как база `BaseDjangoRedisManager` (см. трек B) — таким образом в codex-platform нет необходимости в compat-alias.

A.1. `src/codex_platform/redis_service/operations/hash.py` — добавить `encoder: Callable | None = None` в `set_fields`. Default `None`, не ломает существующих consumers.

A.2. Новый модуль `src/codex_platform/redis_service/operations/sync_string.py`, `operations/sync_hash.py`:
- `SyncStringOperations(redis.Redis)` — `get/set/delete/mget/mset/incr/expire/ttl/exists`.
- `SyncHashOperations(redis.Redis)` — `hget/hset/hdel/hgetall/set_fields`.
- Минимальный набор, используемый codex-django.

A.3. Тесты `tests/unit/test_sync_operations.py` (round-trip, encoder hook).

**Зависимости:** нет. Релизится первым.

**Deliverable:** codex-platform version bump + changelog.

---

### Трек B — codex-django: client factory + sync/async context managers в `BaseDjangoRedisManager`

**Репо:** `C:\install\projects\codex_tools\codex-django`

**Depends on:** A (для sync operations) — либо делать только после A.3.

B.1. `src/codex_django/core/redis/managers/base.py` — переписать `BaseDjangoRedisManager` с нуля. **Не наследуется от `BaseRedisManager`** (codex-platform). Единственный публичный API — 4 context manager'а:

```python
class BaseDjangoRedisManager:
    def __init__(
        self,
        prefix: str = "",
        *,
        async_client_factory: "Callable[[], AsyncRedis] | None" = None,
        sync_client_factory: "Callable[[], SyncRedis] | None" = None,
    ):
        self.prefix = prefix
        self.project_name = get_project_name()
        self._redis_url = get_redis_url_from_settings()
        self._async_factory = async_client_factory or self._default_async_factory
        self._sync_factory = sync_client_factory or self._default_sync_factory

    def _default_async_factory(self) -> "AsyncRedis":
        from redis.asyncio import Redis
        return Redis.from_url(self._redis_url, decode_responses=True)

    def _default_sync_factory(self) -> "SyncRedis":
        import redis
        return redis.Redis.from_url(self._redis_url, decode_responses=True)

    @asynccontextmanager
    async def async_string(self) -> "AsyncIterator[StringOperations]":
        client = self._async_factory()
        try:
            yield StringOperations(client)
        finally:
            await client.aclose()

    @asynccontextmanager
    async def async_hash(self) -> "AsyncIterator[HashOperations]":
        client = self._async_factory()
        try:
            yield HashOperations(client)
        finally:
            await client.aclose()

    @contextmanager
    def sync_string(self) -> "Iterator[SyncStringOperations]":
        client = self._sync_factory()
        try:
            yield SyncStringOperations(client)
        finally:
            client.close()

    @contextmanager
    def sync_hash(self) -> "Iterator[SyncHashOperations]":
        client = self._sync_factory()
        try:
            yield SyncHashOperations(client)
        finally:
            client.close()

    def make_key(self, key: str) -> str: ...
```

Правила (жёсткие):
- `self._client`, `self.string`, `self.hash` как **атрибуты** — удалены. Если найдутся в коде после миграции — не мержим.
- Все sync use-sites: `with mgr.sync_string() as s: s.get(...)`.
- Все async use-sites: `async with mgr.async_string() as s: await s.get(...)`.
- `async_to_sync` из sync Django hot paths удаляется — sync backend использует `sync_string/sync_hash` напрямую.

B.2. `src/codex_django/cache/backends/redis.py`:
- sync методы (`get/set/delete/has_key/clear/...`) — через `sync_string()`/`sync_hash()`.
- async методы (`aget/aset/...`) — через `async_string()`/`async_hash()`.
- `async_to_sync` удалить из sync path полностью.

B.3. `src/codex_django/sessions/backends/redis.py`:
- `save/load/exists/create/delete` — через `sync_string()`.
- `asave/aload/aexists/acreate/adelete` — через `async_string()`.

B.4. `src/codex_django/system/redis/managers/fixtures.py` — мигрировать на `sync_string()/async_string()`.

B.5. Тесты:
- `tests/unit/core/redis/test_base_manager_client_factory.py` — default async/sync factories, injection, `aclose/close` вызывается.
- `tests/unit/sessions/test_redis_backend_sync.py` — sync path.
- `tests/unit/cache/test_redis_backend_sync.py` — sync path.

**Deliverable:** codex-django version bump (minor, т.к. ломающее изменение в signature BaseDjangoRedisManager).

---

### Трек C — codex-django: CacheCoder расширение + `DjangoSiteSettingsManager` typed restore

**Репо:** codex-django. **Depends on:** B (использует новые `hash()`/`ahash()`).

C.1. `src/codex_django/cache/values.py` — расширить CacheCoder:
- `dump_bool(v) → "1"|"0"`; `load_bool(raw) → True|False`.
- `dump_none() → ""`; `load_none` — только явный вызов из typed restore (не автоматический).
- `dump_enum(v) → CacheCoder.dump(v.value)` (рекурсивно, т.к. value может быть dict/bool/None).
- `dump_path(v) → str(v)`.
- `dump_lazy(v) → force_str(v)` (`django.utils.functional.Promise`).
- В generic `dump()` — `isinstance(value, bool)` ДО `int`.

C.2. Тесты `tests/unit/cache/test_values.py` — round-trip всех типов. Для Promise — `override_settings(USE_I18N=True)` + `gettext_lazy`.

C.3. `src/codex_django/core/redis/managers/settings.py`:

**Запись** (sync):
```python
data = instance.to_dict()
coded = {k: CacheCoder.dump(v) for k, v in data.items()}
with self.sync_hash() as h:
    h.set_fields(self.make_key(...), coded)
```

**Чтение** (sync):
```python
with self.sync_hash() as h:
    raw = h.hgetall(self.make_key(...))
return self._decode_fields(raw, instance_cls=SiteSettings)
```

Async-пары (`asave_instance`, `aload_cached`) — через `async_hash()`.

Метод `_decode_fields(raw: dict[str,str], instance_cls)`:
- Идёт по `instance_cls._meta.get_fields()`.
- Для `BooleanField`:
  - `raw[name] == "1"` → `True`;
  - `"0"` → `False`;
  - `""` + `field.null=True` → `None`;
  - иначе fallback на дефолт поля.
- Для `CharField/TextField` — `raw[name]` as-is (пустая строка **не** превращается в None).
- Для nullable non-string полей (`IntegerField(null=True)`, `DateTimeField(null=True)` и т.п.) — `"" → None`.
- Для `DateTimeField/DateField/TimeField/DecimalField/UUIDField` — `CacheCoder.load_*`.
- Для полей, которые модель хранит как JSON (ForeignKey id / JSONField) — `json.loads` либо соответствующий loader.

C.4. Тесты:
- `tests/unit/core/redis/test_settings_manager_encoding.py` — write bool/None/datetime/Decimal/UUID → read с typed restore, включая `BooleanField(null=True)` edge cases.

---

### Трек D — codex-django: `DashboardRedisManager`, SEO selectors, остальные менеджеры

**Репо:** codex-django. **Depends on:** B.

D.1. `src/codex_django/cabinet/redis/managers/dashboard.py`:
- Заменить все `self._client.*` на `with self.sync_string() as s: s.get/set/delete(...)` (sync) и `async with self.async_string() as s: await s.get/set/delete(...)` (async).
- TTL — через `s.set(key, value, ex=ttl)`.

D.2. `src/codex_django/cabinet/selector/dashboard.py:41` — убрать `_manager = DashboardRedisManager()`; заменить на:
```python
@lru_cache(maxsize=1)
def get_dashboard_redis_manager() -> DashboardRedisManager:
    return DashboardRedisManager()
```
Все использования `_manager` переписать на `get_dashboard_redis_manager()`.

D.3. `src/codex_django/core/seo/selectors.py` — аналогично:
- убрать module-level manager;
- `_client` удалить; мигрировать sync на `sync_string()`, async на `async_string()`.

D.4. Grep-gate (обязательно перед мержем в каждом треке B/C/D/E):
```
rg "self\._client|\.string\.|\.hash\." src/codex_django src/codex_platform src/lily_backend
```
Разрешённые находки — только внутри operation-классов codex-platform (`HashOperations`, `StringOperations`, `SyncHashOperations`, `SyncStringOperations`), где `self._client` — это injected redis client этого operation-класса (не менеджер). Всё остальное — мигрировать.

D.5. Проверка оставшихся менеджеров: `NotificationsCacheManager`, `DjangoSiteSettingsManager` (уже в треке C), `FixtureHashManager` (в треке B), локальные `ActionTokenRedisManager` (в lily_website — трек E).

D.6. Тесты:
- `tests/unit/cabinet/redis/test_dashboard_manager.py` — sync get/set/delete, async aget/aset/adelete.
- `tests/unit/core/seo/test_seo_selector_redis.py` — повторные вызовы в одном процессе.

---

### Трек E — lily_website: тесты, локальный workaround, local managers

**Репо:** `C:\install\projects\clients\lily_website`. **Depends on:** B, C, D через editable install из `C:\install\projects\codex_tools\`.

E.1. Удалить локальный bool/None workaround в `src/lily_backend/system/models/settings.py:89-98` — пусть `to_dict()` возвращает нативные Python-значения; CacheCoder применяется централизованно.

E.2. Локальные менеджеры в `src/lily_backend/system/redis.py` (`ActionTokenRedisManager`) — мигрировать на новый контракт (`sync_string()/async_string()`).

E.3. Regression tests в `tests/lily_backend/regression/`:
- `test_dashboard_manager_cache.py` — `Client.force_login(staff)`, `GET /ru/cabinet/` × 2 (первый → cache write, второй → cache read) с `cache_ttl=300`. Оба 200.
- `test_session_event_loop.py` — admin login + 3 GET.
- `test_fixture_hash_repeated.py` — `get_hash/set_hash` × 2.
- `test_site_settings_bool_hset.py` — `DjangoSiteSettingsManager.save_instance` с bool/None/datetime + typed restore.
- `test_seo_static_page.py` — `get_static_page_seo("team")` × 2.

E.4. Integration tests in `tests/lily_backend/integration/` (требуют Docker redis):
- `test_cache_get_set_repeat.py` — sync `cache.set/get/delete` × 10.
- `test_management_commands.py` — двойной `update_site_settings --force`, `update_all_content`, `load_catalog`.
- `test_admin_login_flow.py` — login через `Client` + несколько админ-страниц.

E.5. Unit tests:
- `tests/lily_backend/unit/test_cache_coder_extensions.py` — sanity check, что проектные модели сериализуются.

---

### Трек F — lily_website: feature flag rollout (staging → prod)

**Зависит от:** зелёных A/B/C/D/E и Docker smoke.

F.1. `src/lily_backend/core/settings/prod.py` — feature flag:
```python
USE_CODEX_REDIS_BACKENDS = env.bool("USE_CODEX_REDIS_BACKENDS", default=False)

if USE_CODEX_REDIS_BACKENDS:
    CACHES = {"default": {"BACKEND": "codex_django.cache.backends.redis.RedisCache", ...}}
    SESSION_ENGINE = "codex_django.sessions.backends.redis"
else:
    CACHES = {"default": {"BACKEND": "django_redis.cache.RedisCache", ...}}
    SESSION_ENGINE = "django.contrib.sessions.backends.db"
```

F.2. **`django-redis` оставить в deps** в этом релизе. Удалять — только после успешной работы с flag=True в prod ≥ 2 недели.

F.3. `deploy/lily_backend/entrypoint.sh` — **не** возвращать startup-команды. `update_all_content` — one-shot:
```
docker compose -f docker-compose.prod.yml run --rm -T backend python manage.py update_all_content
```

F.4. Rollout:
- staging: `USE_CODEX_REDIS_BACKENDS=true` → наблюдение логов ≥ 1 рабочий день.
- prod: включить flag; при ошибках — откат переменной окружения без редеплоя кода.

F.5. Runbook в `docs/redis-feature-flag.md`: включение/выключение, что мониторить, куда смотреть логи.

---

### Трек G — infra: Redis password escaping

G.1. Проверить `deploy/docker-compose.prod.yml` + `.env`:
```
docker compose --env-file .env -f docker-compose.prod.yml config
```
Если видим `The "ATTV6fkq" variable is not set` — `$` в пароле интерполируется. Фикс:
- экранировать как `$$` в `.env` / `docker-compose.yml` ИЛИ
- завернуть пароль в одинарные кавычки ИЛИ
- перегенерировать пароль без `$`.

G.2. Добавить guard в entrypoint: проверка, что `REDIS_URL` парсится и содержит непустой пароль; если нет — exit с понятным сообщением.

G.3. Не зависит от A-F. Можно делать параллельно.

---

## Verification (общая)

1. `cd codex-platform && pytest` — трек A зелёный.
2. `cd codex-django && pytest` — треки B/C/D зелёные.
3. `cd lily_website && pytest tests/lily_backend/unit` — трек E unit зелёный.
4. Поднять Docker redis, `pytest tests/lily_backend/integration tests/lily_backend/regression` — зелёные.
5. Docker smoke:
   ```
   docker compose -f deploy/docker-compose.yml up -d redis backend
   docker exec lily_website-backend python manage.py update_site_settings --force
   docker exec lily_website-backend python manage.py update_site_settings --force   # 2-й
   docker exec lily_website-backend python manage.py update_all_content
   docker exec lily_website-backend python manage.py load_catalog
   docker exec lily_website-backend python manage.py shell -c \
     "from django.core.cache import cache; cache.set('redis_check','ok',30); print(cache.get('redis_check'))"
   # Browser: admin login + /ru/cabinet/ × 2 + /ru/team/ + /ru/contacts/
   # Логи: без AttributeError, Event loop is closed, Future attached to different loop, DataError.
   ```
6. **Acceptance metric:** `/ru/cabinet/` p95 в staging с `USE_CODEX_REDIS_BACKENDS=true` не хуже чем с hotfix'ом на ≥50ms. При превышении — follow-up на connection pool / loop-local strong cache.
7. Трек G: `docker compose config` без warnings.

## Critical files (сводка)

**codex-platform** (`C:\install\projects\codex_tools\codex-platform\src\codex_platform\redis_service\`):
- `operations/hash.py` — `encoder` параметр.
- `operations/sync_string.py`, `operations/sync_hash.py` — новые sync-operations.
- `base.py` — без изменений; `BaseRedisManager` остаётся async-only service-layer базой и больше не используется codex-django.

**codex-django** (`C:\install\projects\codex_tools\codex-django\src\codex_django\`):
- `core/redis/managers/base.py` — `BaseDjangoRedisManager` переписан: client factory, 4 context manager'а (`sync_string`, `sync_hash`, `async_string`, `async_hash`), не наследуется от `BaseRedisManager`.
- `cache/backends/redis.py` — sync через `sync_string()/sync_hash()`.
- `sessions/backends/redis.py` — sync через `sync_string()`.
- `system/redis/managers/fixtures.py` — через `sync_string()/async_string()`.
- `cache/values.py` — CacheCoder extensions.
- `core/redis/managers/settings.py` — write с CacheCoder, read с typed restore.
- `cabinet/redis/managers/dashboard.py` — через `sync_string()/async_string()`.
- `cabinet/selector/dashboard.py:41` — lazy `get_dashboard_redis_manager()`.
- `core/seo/selectors.py` — то же.
- `core/redis/managers/notifications.py` — проверить, мигрировать.

**lily_website** (`C:\install\projects\clients\lily_website\src\lily_backend\`):
- `system/models/settings.py:89-98` — удалить workaround.
- `system/redis.py` — мигрировать `ActionTokenRedisManager`.
- `core/settings/prod.py` — feature flag `USE_CODEX_REDIS_BACKENDS`.

## Risks / open questions

- **Performance:** new-client-per-operation. Acceptance metric p95 +50ms max — иначе follow-up. Оптимизация: connection pool на уровне factory (не client) — `redis.Redis(connection_pool=pool)` с общим pool; pool thread-safe, но async pool — нет. Для first-fix не делаем.
- **Breaking change BaseDjangoRedisManager:** публичный API полностью меняется (`self.string`/`self.hash`/`self._client` удалены). Т.к. библиотеки в alpha и единственный consumer — lily_website, compat-слой не тащим. Bump codex-django major (0.x → 0.(x+1)) + changelog с migration guide.
- **Grep-gate не проходит — не мержим.** Любое оставшееся `self._client` / `.string.` / `.hash.` вне operation-классов codex-platform = 500 в проде.
- **CharField "" vs None:** typed restore не превращает пустую строку в None для CharField/TextField.
- **Enum с non-primitive value:** `dump_enum` рекурсивно через `CacheCoder.dump(value.value)` — покрывает.
- **Windows vs Linux asyncio:** smoke только в Linux-контейнере.
- **Координация релизов:** codex-platform → codex-django → lily_website pin commit. Editable install in dev; pinned in prod.
- **django-redis как fallback:** оставляем в deps, не удаляем в этом PR. Удалять — отдельным cleanup после ≥ 2 недель успеха с flag=True.
