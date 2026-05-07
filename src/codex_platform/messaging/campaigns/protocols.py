"""Campaign messaging protocols."""

from __future__ import annotations

from typing import Protocol

from .dto import CampaignBatchDTO


class CampaignDispatcher(Protocol):
    """Enqueues campaign batches for worker-side delivery."""

    def enqueue_batch(self, batch: CampaignBatchDTO) -> str:
        """Enqueue a batch and return the backend job identifier."""
        ...


__all__ = ["CampaignDispatcher"]
