"""Deprecated compatibility imports for :mod:`codex_platform.messaging.delivery.arq`."""

from __future__ import annotations

import warnings

warnings.warn(
    "codex_platform.notifications.delivery.arq is deprecated; use codex_platform.messaging.delivery.arq instead.",
    DeprecationWarning,
    stacklevel=2,
)

from codex_platform.messaging.delivery.arq import *  # noqa: E402,F401,F403
