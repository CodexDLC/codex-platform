"""
codex_platform.redis_service.keys
================================
Redis Key Registry — typed, centralized key definitions.

Eliminates "magic strings" and prevents key format mismatches
across multiple containers (bot, workers, API) that share the same Redis.

Usage::

    class UserKey(BaseRedisKey):
        template = "u:{user_id}"

    key = UserKey().build(user_id=42)          # → "u:42"

    # Or via resolve_key:
    from codex_platform.redis_service.keys import resolve_key
    resolve_key(UserKey(), user_id=42)         # → "u:42"
    resolve_key("u:42")                        # → "u:42"

Extending for project-specific keys::

    from codex_platform.redis_service.keys import BaseRedisKey

    class JobStatusKey(BaseRedisKey):
        template = "arq:job:{job_id}:status"
"""

from abc import ABC, abstractmethod
from typing import Any


class BaseRedisKey(ABC):
    """
    Abstract base for all Redis key definitions.

    Subclass and define `template` with ``{placeholder}`` syntax.
    Call ``.build(**kwargs)`` to construct the final key string.
    """

    @property
    @abstractmethod
    def template(self) -> str:
        """Key template string with ``{placeholder}`` syntax."""

    def build(self, **kwargs: Any) -> str:
        """Build the final key string by formatting the template with keyword arguments.

        Args:
            **kwargs: Values for each placeholder defined in ``template``.

        Returns:
            Fully resolved Redis key string.

        Raises:
            ValueError: If a required placeholder argument is missing.
        """
        try:
            return self.template.format(**kwargs)
        except KeyError as e:
            raise ValueError(f"Missing key argument: {e} for template '{self.template}'") from e

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(template={self.template!r})"


def resolve_key(key: "str | BaseRedisKey", **kwargs: Any) -> str:
    """Resolve a key that is either a plain string or a ``BaseRedisKey`` instance.

    If ``key`` is a :class:`BaseRedisKey`, calls ``key.build(**kwargs)``.
    If ``key`` is a plain string, returns it unchanged.

    Args:
        key: Redis key string or a ``BaseRedisKey`` instance.
        **kwargs: Placeholder values forwarded to ``BaseRedisKey.build``.

    Returns:
        Resolved Redis key string.

    Example::

        resolve_key(UserKey(), user_id=42)   # → "u:42"
        resolve_key("u:42")                  # → "u:42"
    """
    return key.build(**kwargs) if isinstance(key, BaseRedisKey) else key


# ---------------------------------------------------------------------------
# Shared keys — common across all services
# ---------------------------------------------------------------------------


class UserKey(BaseRedisKey):
    """User data hash. Args: user_id."""

    template = "u:{user_id}"


class SessionKey(BaseRedisKey):
    """Session data. Args: token."""

    template = "sess:{token}"


__all__ = [
    "BaseRedisKey",
    "resolve_key",
    "UserKey",
    "SessionKey",
]
