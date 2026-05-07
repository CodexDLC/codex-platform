"""Deprecated compatibility imports for :mod:`codex_platform.messaging.delivery`."""

from __future__ import annotations

import warnings

warnings.warn(
    "codex_platform.notifications.delivery is deprecated; use codex_platform.messaging.delivery instead.",
    DeprecationWarning,
    stacklevel=2,
)

from codex_platform.messaging.delivery import *  # noqa: E402,F401,F403
