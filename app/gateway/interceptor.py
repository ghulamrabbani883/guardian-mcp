
"""
MCP Guardian - Tool Interceptor
"""

from typing import Any
import logging

from app.approval.manager import ApprovalManager
logger = logging.getLogger(__name__)

class ToolBlockedError(Exception):
    """Raised when a user denies an MCP tool invocation."""


class ToolInterceptor:
    def __init__(
        self,
        approval_manager: ApprovalManager,
        server_name: str,
    ):
        self.approval_manager = approval_manager
        self.server_name = server_name

    async def authorize(
        self,
        tool_name: str,
        arguments: dict[str, Any] | None,
    ) -> None:
        """
        Hold a tool invocation until an approval decision is received.

        Returns normally only when approved.
        Raises ToolBlockedError when denied.
        """

        safe_arguments = arguments or {}

        logger.info(
            f"[GUARDIAN] Intercepted tools/call: {tool_name}",
            extra={"flush": True},
        )

        allowed = await self.approval_manager.request_approval(
            server_name=self.server_name,
            tool_name=tool_name,
            arguments=safe_arguments,
        )

        if not allowed:
            raise ToolBlockedError(
                f"Guardian blocked execution of tool '{tool_name}'."
            )

        logger.info(
            f"[GUARDIAN] Authorization granted: {tool_name}",
            extra={"flush": True},
        )
