"""Application configuration loaded from JSON."""

import json
import sys
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field, field_validator


class GuardianConfig(BaseModel):
    upstream_command: str = Field(default_factory=lambda: sys.executable)
    upstream_args: list[str] = Field(default_factory=list)
    upstream_name: str = "guardian-test-server"
    approval_timeout: float = Field(default=120.0, gt=0)
    approval_mode: Literal["manual", "allow", "block"] = "manual"
    transport: Literal["stdio", "remote"] = "stdio"
    remote_host: str = "127.0.0.1"
    remote_port: int = Field(default=8000, ge=1, le=65535)
    remote_path: str = "/mcp"
    bearer_token: str | None = None

    @field_validator("remote_path")
    @classmethod
    def validate_remote_path(cls, value: str) -> str:
        if not value.startswith("/"):
            raise ValueError("remote_path must start with '/'")
        return value.rstrip("/") or "/"

    @field_validator("bearer_token")
    @classmethod
    def validate_remote_token(cls, value: str | None) -> str | None:
        if value is not None:
            value = value.strip()
            if len(value) < 16:
                raise ValueError(
                    "bearer_token must contain at least 16 characters"
                )
        return value or None


def load_config(path: str | Path | None) -> GuardianConfig:
    if path is None:
        return GuardianConfig()

    config_path = Path(path).expanduser()
    if not config_path.exists():
        raise FileNotFoundError(f"Configuration file not found: {config_path}")

    with config_path.open("r", encoding="utf-8") as config_file:
        data = json.load(config_file)

    return GuardianConfig.model_validate(data)