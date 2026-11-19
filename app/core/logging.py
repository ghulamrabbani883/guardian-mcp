
import logging
import sys
from collections.abc import Mapping
from typing import Any


SENSITIVE_ARGUMENT_KEYS = frozenset({
    "authorization",
    "cookie",
    "password",
    "passwd",
    "secret",
    "token",
    "api_key",
    "apikey",
    "access_key",
    "private_key",
})


def redact_sensitive_arguments(value: Any) -> Any:
    """Return a copy of argument data with common credential fields redacted."""

    if isinstance(value, Mapping):
        return {
            str(key): (
                "[REDACTED]"
                if str(key).lower() in SENSITIVE_ARGUMENT_KEYS
                else redact_sensitive_arguments(item)
            )
            for key, item in value.items()
        }

    if isinstance(value, list):
        return [redact_sensitive_arguments(item) for item in value]

    if isinstance(value, tuple):
        return tuple(redact_sensitive_arguments(item) for item in value)

    return value


def configure_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        stream=sys.stderr,
    )
