from app.core.logging import redact_sensitive_arguments


def test_redacts_sensitive_nested_arguments():
    original = {
        "query": "safe",
        "headers": {
            "Authorization": "Bearer secret",
            "X-Test": "visible",
        },
        "api_key": "private",
        "items": [{"token": "abc"}],
    }

    redacted = redact_sensitive_arguments(original)

    assert redacted["query"] == "safe"
    assert redacted["headers"]["Authorization"] == "[REDACTED]"
    assert redacted["headers"]["X-Test"] == "visible"
    assert redacted["api_key"] == "[REDACTED]"
    assert redacted["items"][0]["token"] == "[REDACTED]"
    assert original["api_key"] == "private"
