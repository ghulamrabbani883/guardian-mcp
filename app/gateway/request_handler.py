"""Protocol and approval handling helpers for MCP gateway tool calls."""

from typing import Any


class ToolRequestDeniedError(Exception):
    """A tool call was denied before it reached the upstream MCP server."""


def validate_tool_arguments(arguments: dict[str, Any] | None) -> dict[str, Any]:
    if arguments is None:
        return {}
    if not isinstance(arguments, dict):
        raise ValueError("MCP tool arguments must be a JSON object.")
    return arguments


def denied_tool_message(tool_name: str) -> str:
    return f"Guardian blocked execution of tool '{tool_name}'."