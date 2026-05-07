"""Campaign messaging DTOs."""

from __future__ import annotations

from typing import Any

from codex_core.core import BaseDTO
from pydantic import model_validator

from codex_platform.messaging.workers_contract import PAYLOAD_SCHEMA_VERSION


class CampaignRecipientDraft(BaseDTO):
    """Recipient data needed by a campaign batch worker."""

    recipient_id: str
    email: str
    first_name: str = ""
    last_name: str = ""
    locale: str = "de"
    unsubscribe_token: str | None = None


class CampaignBatchDTO(BaseDTO):
    """One campaign batch payload for the worker callback contract."""

    schema_version: int = PAYLOAD_SCHEMA_VERSION
    campaign_id: str
    template_name: str | None = None
    html_content: str | None = None
    subject: str
    recipients: list[CampaignRecipientDraft]
    base_context: dict[str, Any] = {}
    callback_url: str
    callback_token: str

    @model_validator(mode="after")
    def validate_rendering_mode(self) -> CampaignBatchDTO:
        """Require exactly one campaign rendering mode."""

        if bool(self.template_name) == bool(self.html_content):
            raise ValueError("exactly one of template_name or html_content must be set")
        return self


__all__ = ["CampaignRecipientDraft", "CampaignBatchDTO"]
