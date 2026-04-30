# Migration: `codex_platform.notifications` → `codex_platform.messaging`

## Decision

The `messaging` package is created **inside the existing
codex-platform repo** as a sibling package to `notifications`. The
old `notifications` package becomes a thin alias for one minor release,
then is removed.

This is the lowest-risk option: no new repo, no new wheel to publish,
no version-skew between `messaging` and `notifications` to manage.

## Renames (1:1, no semantic changes)

| Old import | New import |
|------------|------------|
| `from codex_platform.notifications import NotificationPayloadDTO` | `from codex_platform.messaging import NotificationPayloadDTO` |
| `from codex_platform.notifications import TemplateNotificationDTO` | `from codex_platform.messaging import TemplateNotificationDTO` |
| `from codex_platform.notifications import RenderedNotificationDTO` | `from codex_platform.messaging import RenderedNotificationDTO` |
| `from codex_platform.notifications import NotificationRecipient` | `from codex_platform.messaging import NotificationRecipient` |
| `from codex_platform.notifications import NotificationChannel` | `from codex_platform.messaging import NotificationChannel` |
| `from codex_platform.notifications import AsyncEmailClient` | `from codex_platform.messaging import AsyncEmailClient` |
| `from codex_platform.notifications import BaseDeliveryOrchestrator` | `from codex_platform.messaging import BaseDeliveryOrchestrator` |
| `from codex_platform.notifications import ChannelRegistry` | `from codex_platform.messaging import ChannelRegistry` |
| `from codex_platform.notifications import ContentProvider` | `from codex_platform.messaging import ContentProvider` |
| `from codex_platform.notifications import ContentCacheAdapter` | `from codex_platform.messaging import ContentCacheAdapter` |
| `from codex_platform.notifications.delivery import ArqNotificationAdapter` | `from codex_platform.messaging.delivery import ArqNotificationAdapter` |
| `from codex_platform.notifications.delivery import DirectNotificationAdapter` | `from codex_platform.messaging.delivery import DirectNotificationAdapter` |
| `from codex_platform.notifications.delivery import NotificationAdapter` | `from codex_platform.messaging.delivery import NotificationAdapter` |
| `from codex_platform.notifications.renderer import TemplateRenderer` | `from codex_platform.messaging.renderer import TemplateRenderer` |
| `from codex_platform.notifications.clients.smtp import AsyncEmailClient` | `from codex_platform.messaging.clients.smtp import AsyncEmailClient` |

Same shape, same arguments, same behavior.

## Additions (new in `messaging`)

| New symbol | Module | Purpose |
|------------|--------|---------|
| `ThreadHeadersDTO` | `messaging.dto` | RFC 5322 thread headers, promoted from worker. |
| `CampaignRecipientDraft` | `messaging.campaigns.dto` | Replaces `RecipientDraft` in lily. |
| `CampaignBatchDTO` | `messaging.campaigns.dto` | Replaces ad-hoc batch payload. |
| `AudienceBuilder` | `messaging.audience` | Promoted from `features/conversations/campaigns/audience.py`. |
| `CampaignDispatcher` | `messaging.campaigns` | Promoted from `features/conversations/campaigns/dispatcher.py`. |
| `SendGridChannel` | `messaging.clients.sendgrid` | Promoted from worker `email_client.py`. |
| `messaging.threading.*` helpers | `messaging.threading` | Promoted from worker `_mailbox_headers()`. |
| `messaging.workers_contract` | `messaging.workers_contract` | Constants for task names + schema version. |

## Alias module

For one minor release, `codex_platform/notifications/__init__.py`
becomes a deprecation shim:

```python
"""
DEPRECATED. Imports moved to codex_platform.messaging.

This module re-exports the new names so legacy code keeps working.
Will be removed in codex-platform 1.x+1.
"""

import warnings

warnings.warn(
    "codex_platform.notifications is deprecated; "
    "use codex_platform.messaging instead.",
    DeprecationWarning,
    stacklevel=2,
)

from codex_platform.messaging import *  # noqa: F401,F403
from codex_platform.messaging.delivery import (  # noqa: F401
    ArqNotificationAdapter,
    DirectNotificationAdapter,
    NotificationAdapter,
)
```

The same pattern applies to:
* `codex_platform/notifications/dto.py`
* `codex_platform/notifications/channels.py`
* `codex_platform/notifications/clients/smtp.py`
* `codex_platform/notifications/orchestrator.py`
* `codex_platform/notifications/registry.py`
* `codex_platform/notifications/interfaces.py`
* `codex_platform/notifications/renderer.py`
* `codex_platform/notifications/delivery/*.py`

Each shim emits one `DeprecationWarning` on import (not on each
attribute access).

## Behavior changes during migration

The rename is **purely cosmetic** for the existing surface. The
following behavior changes happen at the same time but are
**additive** — they do not break old call sites:

1. **`DeliveryChannel.send` gains `headers` keyword.** The default is
   `None`; existing channels keep working. New channels are expected
   to honor it.
2. **New tasks register via `messaging.workers_contract.TASK_*`
   constants.** Existing string literals continue to work.

## Test coverage during migration

Tests in `codex-platform/tests/notifications/` remain green by
adjusting only imports. A new mirrored suite `tests/messaging/`
imports from the new path. Both suites run during the deprecation
window. After deprecation, the old suite is deleted.

## Migration timeline

| Step | What | Owner |
|------|------|-------|
| 1 | Create `src/codex_platform/messaging/` mirroring `notifications/`. Copy + repath. | platform |
| 2 | Add new symbols (`ThreadHeadersDTO`, `SendGridChannel`, …). | platform |
| 3 | Replace `notifications/__init__.py` etc. with deprecation shims. | platform |
| 4 | Update `codex_django.notifications` → `codex_django.messaging` (separate doc set, same pattern). | django |
| 5 | Each consumer project bumps codex-platform, switches imports at its own pace. | projects |
| 6 | After 1 minor release with shims live: delete `notifications` shims. | platform |

## Rollback

If a regression appears:

1. Revert step 3 (delete the messaging side, restore the old
   `notifications/` files). Both `messaging` and `notifications`
   imports work from old code.
2. The new symbols in step 2 stay (they were additive).
3. Consumers stay on either import path.

The migration is reversible right up to step 6. Once the shims are
deleted, downstream consumers must already be on the new path.

## CI checks that must be added

* A linter pass that fails the build if any file inside
  `src/codex_platform/messaging/` imports `django` or `codex_django`.
* A linter pass that warns when any project file imports from
  `codex_platform.notifications` (already-DeprecationWarning at
  runtime, but a static check makes the migration tractable).
