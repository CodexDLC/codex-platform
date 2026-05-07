"""Deprecated compatibility imports for :mod:`codex_platform.messaging`."""

from __future__ import annotations

import warnings

warnings.warn(
    "codex_platform.notifications is deprecated; use codex_platform.messaging instead.",
    DeprecationWarning,
    stacklevel=2,
)

from codex_platform.messaging import *  # noqa: E402,F401,F403
