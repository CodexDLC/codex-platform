"""Audience selection contracts for campaign messaging."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any, Protocol

from .campaigns.dto import CampaignRecipientDraft


class AudienceBuilder(Protocol):
    """Materializes campaign recipients from a host-defined filter."""

    def count(self, audience_filter: dict[str, Any]) -> int:
        """Return the number of recipients matching the filter."""
        ...

    def materialize(self, audience_filter: dict[str, Any]) -> Iterable[CampaignRecipientDraft]:
        """Stream recipient drafts matching the filter."""
        ...


__all__ = ["AudienceBuilder"]
