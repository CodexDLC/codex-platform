"""ARQ adapter — producer-side client for Django (enqueue jobs into ARQ queue)."""

from .client import BaseArqClient

__all__ = ["BaseArqClient"]
