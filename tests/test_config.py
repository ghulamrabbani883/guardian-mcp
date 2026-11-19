import json

import pytest

from app.core.config import GuardianConfig, load_config


def test_load_config(tmp_path):
    path = tmp_path / "guardian.json"
    path.write_text(
        json.dumps({
            "upstream_command": "python3",
            "upstream_args": ["server.py"],
            "transport": "remote",
            "remote_port": 9000,
            "bearer_token": "0123456789abcdef",
        }),
        encoding="utf-8",
    )

    config = load_config(path)

    assert config.transport == "remote"
    assert config.remote_port == 9000
    assert config.upstream_args == ["server.py"]


def test_config_rejects_invalid_remote_port():
    with pytest.raises(ValueError):
        GuardianConfig(remote_port=70000)


def test_config_rejects_short_bearer_token():
    with pytest.raises(ValueError):
        GuardianConfig(bearer_token="short")
