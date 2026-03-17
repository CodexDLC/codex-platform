"""
codex_platform.worker.arq.types
================================
Common type definitions for worker dependency injection.
"""

from collections.abc import Awaitable, Callable
from typing import Any

# Type for dependency init/close functions used in worker startup/shutdown lists
DependencyFunction = Callable[[dict[str, Any], Any], Awaitable[None]]
