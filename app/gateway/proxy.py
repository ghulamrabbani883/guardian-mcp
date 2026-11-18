
"""
MCP Guardian - Stdio Interception Proxy

Acts as:
- An MCP client towards the original server.
- An MCP server towards Claude Desktop.

All tool calls pass through the approval interceptor.
"""

from typing import Any
import logging

from mcp import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client
from mcp.server.lowlevel import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool

from app.approval.manager import ApprovalManager
from app.gateway.interceptor import ToolInterceptor

logger = logging.getLogger(__name__)


async def discover_upstream_tools(
    upstream: ClientSession,
) -> list[Tool]:
    """Discover all upstream tools, including paginated results."""

    tools: list[Tool] = []
    cursor: str | None = None

    while True:
        result = await upstream.list_tools(cursor=cursor)

        tools.extend(result.tools)

        cursor = result.nextCursor

        if not cursor:
            break

    return tools


async def run_proxy(
    upstream_command: str,
    upstream_args: list[str],
    approval_mode: str = "manual",
    approval_timeout: float = 120.0,
    upstream_name: str = "guardian-test-server",
) -> None:
    """Start the upstream server and expose the Guardian MCP gateway."""

    approval_manager = ApprovalManager(
        mode=approval_mode,
        timeout=approval_timeout,
    )

    interceptor = ToolInterceptor(
        approval_manager=approval_manager,
        server_name=upstream_name,
    )

    server_params = StdioServerParameters(
        command=upstream_command,
        args=upstream_args,
    )

    # Connection 1: Guardian -> Original MCP Server
    async with stdio_client(server_params) as (
        upstream_read,
        upstream_write,
    ):
        async with ClientSession(
            upstream_read,
            upstream_write,
        ) as upstream:

            initialization = await upstream.initialize()

            logger.info(
                "[GUARDIAN] Upstream MCP connection established.",
                extra={"flush": True},
            )

            tools = await discover_upstream_tools(upstream)

            tool_registry = {
                tool.name: tool
                for tool in tools
            }

            logger.info(
                f"[GUARDIAN] Discovered {len(tools)} upstream tools.",
                extra={"flush": True},
            )

            # Connection 2: Claude -> Guardian
            guardian_server = Server(
                "mcp-guardian",
                version="0.1.0",
                instructions=(
                    "MCP Guardian intercepts tool invocations "
                    "and requires approval before execution."
                ),
            )

            @guardian_server.list_tools()
            async def handle_list_tools() -> list[Tool]:
                """Expose discovered upstream tools downstream."""

                return tools

            @guardian_server.call_tool()
            async def handle_call_tool(
                name: str,
                arguments: dict[str, Any],
            ):
                """Intercept and conditionally forward tool invocations."""

                # Reject calls to tools that were not discovered.
                if name not in tool_registry:
                    raise ValueError(
                        f"Unknown upstream tool: {name}"
                    )

                safe_arguments = arguments or {}

                # Security boundary: execution cannot proceed
                # until the approval manager returns True.
                await interceptor.authorize(
                    tool_name=name,
                    arguments=safe_arguments,
                )

                # This line is reached ONLY after approval.
                result = await upstream.call_tool(
                    name,
                    safe_arguments,
                )

                if result.isError:
                    error_text = "\n".join(
                        item.text
                        for item in result.content
                        if hasattr(item, "text")
                    )

                    raise RuntimeError(
                        error_text or "Upstream tool execution failed."
                    )

                return result.content

            logger.info(
                "[GUARDIAN] Gateway ready. Waiting for MCP client.",
                extra={"flush": True},
            )

            async with stdio_server() as (
                downstream_read,
                downstream_write,
            ):
                await guardian_server.run(
                    downstream_read,
                    downstream_write,
                    guardian_server.create_initialization_options(),
                )
