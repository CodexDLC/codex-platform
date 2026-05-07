"""Deprecated compatibility imports for :mod:`codex_platform.messaging.renderer`."""

from __future__ import annotations

import warnings

warnings.warn(
    "codex_platform.notifications.renderer is deprecated; use codex_platform.messaging.renderer instead.",
    DeprecationWarning,
    stacklevel=2,
)

from codex_platform.messaging.renderer import *  # noqa: E402,F401,F403
