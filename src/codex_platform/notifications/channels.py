"""Deprecated compatibility imports for :mod:`codex_platform.messaging.channels`."""

from __future__ import annotations

import warnings

warnings.warn(
    "codex_platform.notifications.channels is deprecated; use codex_platform.messaging.channels instead.",
    DeprecationWarning,
    stacklevel=2,
)

from codex_platform.messaging.channels import *  # noqa: E402,F401,F403
