import json
import re

SENSITIVE = re.compile(r"password|secret|token|authorization|cookie|api[_-]?key|private[_-]?key", re.I)


def sanitize(value, depth=0):
    if depth > 15:
        return "[TRUNCATED]"
    if isinstance(value, dict):
        return {str(k): "[REDACTED]" if SENSITIVE.search(str(k)) else sanitize(v, depth + 1)
                for k, v in list(value.items())[:100]}
    if isinstance(value, list):
        return [sanitize(v, depth + 1) for v in value[:100]]
    if isinstance(value, str):
        value = re.sub(r"(?i)Bearer\s+[^\s\"']+", "Bearer [REDACTED]", value)
        value = re.sub(r"(?i)((?:password|secret|token|api[_-]?key)\s*[=:]\s*)[^\s,;]+", r"\1[REDACTED]", value)
        return value[:4096]
    return value


def response_body(raw: bytes):
    try:
        value = json.loads(raw)
    except (ValueError, UnicodeDecodeError):
        # Unknown text can include secrets with arbitrary labels; don't retain it.
        return {"note": "Non-JSON response omitted", "bytes": len(raw)}
    return sanitize(value)


def sensitive_keys(value):
    if isinstance(value, dict):
        return [str(k) for k, v in value.items() if SENSITIVE.search(str(k)) and v not in (None, "")] + [
            key for v in value.values() for key in sensitive_keys(v)]
    if isinstance(value, list):
        return [key for v in value for key in sensitive_keys(v)]
    return []
