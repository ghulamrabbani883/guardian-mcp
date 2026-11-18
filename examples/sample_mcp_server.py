
"""
MCP Guardian - Sample Upstream MCP Server

A harmless MCP server used to verify that Guardian can:
1. Discover available tools.
2. Invoke tools.
3. Observe whether an operation was executed.
"""
import sys
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("guardian-test-server")


@mcp.tool()
def get_server_status() -> dict:
    """Return the status of the sample MCP server."""

    print("[UPSTREAM] get_server_status EXECUTED", file=sys.stderr)
    return {
        "server": "guardian-test-server",
        "status": "running",
        "guardian_test": True,
    }


@mcp.tool()
def add_numbers(a: float, b: float) -> dict:
    """Add two numbers and return the result."""

    print(
    f"[UPSTREAM] add_numbers EXECUTED: {a} + {b}",
    file=sys.stderr,
)

    return {
        "a": a,
        "b": b,
        "result": a + b,
    }


if __name__ == "__main__":
    mcp.run(transport="stdio")
