"""Streamable HTTP MCP gateway for remote Claude connectors."""

import asyncio
import logging
from contextlib import asynccontextmanager
from typing import Any

import uvicorn
from mcp import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client
from mcp.server.lowlevel import Server
from mcp.server.fastmcp.server import StreamableHTTPASGIApp
from mcp.server.streamable_http_manager import StreamableHTTPSessionManager
from mcp.types import Tool
from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route

from app.approval.manager import ApprovalManager
from app.gateway.interceptor import ToolInterceptor
from app.gateway.proxy import discover_upstream_tools


logger = logging.getLogger(__name__)


class BearerTokenMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, bearer_token: str):
        super().__init__(app)
        self.bearer_token = bearer_token

    async def dispatch(self, request: Request, call_next):
        authorization = request.headers.get("authorization", "")
        expected = f"Bearer {self.bearer_token}"
        if authorization != expected:
            return JSONResponse(
                {"error": "Unauthorized"},
                status_code=401,
                headers={"WWW-Authenticate": "Bearer"},
            )
        return await call_next(request)


@asynccontextmanager
async def remote_lifespan(
    session_manager: StreamableHTTPSessionManager,
):
    async with session_manager.run():
        yield


async def run_remote_gateway(
    upstream_command: str,
    upstream_args: list[str],
    approval_manager: ApprovalManager,
    host: str = "127.0.0.1",
    port: int = 8000,
    path: str = "/mcp",
    bearer_token: str | None = None,
    upstream_name: str = "guardian-test-server",
) -> None:
    """Expose an approved gateway over Streamable HTTP."""

    if not bearer_token or len(bearer_token) < 16:
        raise ValueError(
            "Remote Claude Web support requires a bearer token with at least "
            "16 characters."
        )

    server_params = StdioServerParameters(
        command=upstream_command,
        args=upstream_args,
    )

    async with stdio_client(server_params) as (
        upstream_read,
        upstream_write,
    ):
        async with ClientSession(
            upstream_read,
            upstream_write,
        ) as upstream:
            await upstream.initialize()
            tools = await discover_upstream_tools(upstream)
            tool_registry = {tool.name: tool for tool in tools}
            interceptor = ToolInterceptor(
                approval_manager=approval_manager,
                server_name=upstream_name,
            )

            gateway = Server(
                "mcp-guardian",
                version="0.1.0",
                instructions=(
                    "Remote MCP Guardian requires approval before tool execution."
                ),
            )

            @gateway.list_tools()
            async def handle_list_tools() -> list[Tool]:
                return tools

            @gateway.call_tool()
            async def handle_call_tool(
                name: str,
                arguments: dict[str, Any],
            ):
                if name not in tool_registry:
                    raise ValueError(f"Unknown upstream tool: {name}")

                safe_arguments = arguments or {}
                await interceptor.authorize(
                    tool_name=name,
                    arguments=safe_arguments,
                )

                result = await upstream.call_tool(name, safe_arguments)
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

            session_manager = StreamableHTTPSessionManager(
                app=gateway,
                json_response=True,
                stateless=True,
            )

            app = Starlette(
                routes=[
                    Route(
                        path,
                        endpoint=StreamableHTTPASGIApp(session_manager),
                    )
                ],
                middleware=[
                    Middleware(
                        BearerTokenMiddleware,
                        bearer_token=bearer_token,
                    )
                ],
                lifespan=lambda application:
                    remote_lifespan(session_manager),
            )

            logger.info(
                "Starting authenticated remote MCP gateway at "
                "http://%s:%d%s",
                host,
                port,
                path,
            )

            config = uvicorn.Config(
                app,
                host=host,
                port=port,
                log_level="info",
            )
            await uvicorn.Server(config).serve()
