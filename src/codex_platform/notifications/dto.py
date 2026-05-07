"""Deprecated compatibility imports for :mod:`codex_platform.messaging.dto`."""

from __future__ import annotations

import warnings

warnings.warn(
    "codex_platform.notifications.dto is deprecated; use codex_platform.messaging.dto instead.",
    DeprecationWarning,
    stacklevel=2,
)

from codex_platform.messaging.dto import *  # noqa: E402,F401,F403
