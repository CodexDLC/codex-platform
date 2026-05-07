"""Helpers for RFC 5322 email threading headers."""

from __future__ import annotations

import base64
import uuid

from .dto import ThreadHeadersDTO

CODEX_THREAD_HEADER = "X-Codex-Thread-Key"
LEGACY_LILY_THREAD_HEADER = "X-Lily-Thread-Key"


def build_message_id(*, domain: str) -> str:
    """Build a host-scoped RFC 5322 Message-ID."""

    normalized_domain = domain.strip().strip("@")
    if not normalized_domain:
        raise ValueError("domain must not be empty")
    return f"<{uuid.uuid4()}@{normalized_domain}>"


def build_thread_key() -> str:
    """Build an opaque thread key safe to use in email headers and URLs."""

    token = base64.urlsafe_b64encode(uuid.uuid4().bytes).decode("ascii").rstrip("=")
    return f"tk_{token}"


def parse_references(header_value: str) -> list[str]:
    """Parse a References header into individual Message-ID values."""

    return [part for part in header_value.split() if part]


def serialize_references(message_ids: list[str]) -> str:
    """Serialize Message-ID values into a References header."""

    return " ".join(message_ids)


def render_email_headers(dto: ThreadHeadersDTO) -> dict[str, str]:
    """Render thread DTO fields into outbound email headers."""

    headers = {
        "Message-ID": dto.message_id,
        CODEX_THREAD_HEADER: dto.thread_key,
        LEGACY_LILY_THREAD_HEADER: dto.thread_key,
    }
    if dto.in_reply_to:
        headers["In-Reply-To"] = dto.in_reply_to
    if dto.references:
        headers["References"] = serialize_references(dto.references)
    return headers


__all__ = [
    "CODEX_THREAD_HEADER",
    "LEGACY_LILY_THREAD_HEADER",
    "build_message_id",
    "build_thread_key",
    "parse_references",
    "serialize_references",
    "render_email_headers",
]
