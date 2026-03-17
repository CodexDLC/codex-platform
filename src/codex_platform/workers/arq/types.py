"""
codex_platform.workers.arq.types
================================
Common type definitions for workers dependency injection.
"""

from collections.abc import Awaitable, Callable
from typing import Any

# Type for dependency init/close functions used in workers startup/shutdown lists
DependencyFunction = Callable[[dict[str, Any], Any], Awaitable[None]]
