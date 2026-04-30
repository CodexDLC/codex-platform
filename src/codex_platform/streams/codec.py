"""
codex_platform.streams.codec
============================
JSON-safe Redis Stream field encoding.
"""

from __future__ import annotations

import json
from typing import Any

JSON_PREFIX = "json:"


def encode_stream_value(value: Any) -> str:
    """Encode one value for Redis Streams without losing structured types."""
    if isinstance(value, str):
        return value
    return JSON_PREFIX + json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def decode_stream_value(value: bytes | str) -> Any:
    """Decode one Redis Stream field value encoded by :func:`encode_stream_value`."""
    text = value.decode() if isinstance(value, bytes) else value
    if text.startswith(JSON_PREFIX):
        return json.loads(text[len(JSON_PREFIX) :])
    return text


def encode_stream_payload(data: dict[str, Any]) -> dict[str, str]:
    """Encode a payload dict for XADD."""
    return {key: encode_stream_value(value) for key, value in data.items()}


def decode_stream_payload(fields: dict[bytes | str, bytes | str]) -> dict[str, Any]:
    """Decode a Redis Streams fields dict."""
    return {
        key.decode() if isinstance(key, bytes) else key: decode_stream_value(value) for key, value in fields.items()
    }
