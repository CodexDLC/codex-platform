"""Deprecated compatibility imports for :mod:`codex_platform.messaging.clients`."""

from __future__ import annotations

import warnings

warnings.warn(
    "codex_platform.notifications.clients is deprecated; use codex_platform.messaging.clients instead.",
    DeprecationWarning,
    stacklevel=2,
)

from codex_platform.messaging.clients import *  # noqa: E402,F401,F403
