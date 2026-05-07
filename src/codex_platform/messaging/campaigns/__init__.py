"""Campaign messaging DTOs and protocols."""

from .dto import CampaignBatchDTO, CampaignRecipientDraft
from .protocols import CampaignDispatcher

__all__ = ["CampaignRecipientDraft", "CampaignBatchDTO", "CampaignDispatcher"]
