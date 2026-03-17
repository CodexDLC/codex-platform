"""
codex_platform.redis_service.keys
================================
Redis Key Registry — typed, centralized key definitions.

Eliminates "magic strings" and prevents key format mismatches
across multiple containers (bot, worker, API) that share the same Redis.

Usage::

    # Define shared keys in codex_platform:
    class UserKey(BaseRedisKey):
        template = "u:{user_id}"

    # Use in service:
    key = UserKey().build(user_id=42)          # → "u:42"
    await service.get_hash_json(key, "profile")

    # Or pass the key object directly (auto-built in mixins):
    await service.get_hash_json(UserKey(), "profile", user_id=42)

Extending for project-specific keys::

    # In your project:
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

    Example::

        class UserProfileKey(BaseRedisKey):
            template = "u:{user_id}:profile"

        key = UserProfileKey().build(user_id=42)  # → "u:42:profile"
    """

    @property
    @abstractmethod
    def template(self) -> str:
        """Key template string with ``{placeholder}`` syntax."""

    def build(self, **kwargs: Any) -> str:
        """
        Build the final key string from template and arguments.

        Raises:
            ValueError: If a required placeholder argument is missing.
        """
        try:
            return self.template.format(**kwargs)
        except KeyError as e:
            raise ValueError(f"Missing key argument: {e} for template '{self.template}'") from e

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(template={self.template!r})"


# ---------------------------------------------------------------------------
# Shared keys — common across all services
# ---------------------------------------------------------------------------


class UserKey(BaseRedisKey):
    """User data hash. Args: user_id."""

    template = "u:{user_id}"


class SessionKey(BaseRedisKey):
    """Session data. Args: token."""

    template = "sess:{token}"


class StreamKey(BaseRedisKey):
    """Redis Stream name. Args: stream_name."""

    template = "str:{stream_name}"


__all__ = [
    "BaseRedisKey",
    "UserKey",
    "SessionKey",
    "StreamKey",
]
