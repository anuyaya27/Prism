import re
from typing import Any, Dict

SECRET_HEADER_PATTERNS = [
    "authorization",
    "api-key",
    "apikey",
    "x-api-key",
    "x-api-key",
    "token",
]


def redact_headers(headers: Dict[str, Any]) -> Dict[str, Any]:
    cleaned: Dict[str, Any] = {}
    for key, value in headers.items():
        key_lower = key.lower()
        if any(p in key_lower for p in SECRET_HEADER_PATTERNS):
            cleaned[key] = "***REDACTED***"
        else:
            cleaned[key] = value
    return cleaned


def redact_payload(payload: Any) -> Any:
    """Basic redaction: masks long token-like strings in nested dict/list/str structures."""
    if isinstance(payload, dict):
        return {k: redact_payload(v) for k, v in payload.items()}
    if isinstance(payload, list):
        return [redact_payload(v) for v in payload]
    if isinstance(payload, str):
        if len(payload) > 24 and re.search(r"[A-Za-z0-9]{20,}", payload):
            return payload[:4] + "***REDACTED***" + payload[-4:]
        return payload
    return payload


def sanitize_raw_io(url: str | None = None, headers: Dict[str, Any] | None = None, body: Any | None = None) -> Dict[str, Any]:
    return {
        "url": url,
        "headers": redact_headers(headers or {}),
        "body": redact_payload(body) if body is not None else None,
    }
