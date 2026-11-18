
"""
MCP Guardian - Approval Manager

Maintains independent approval decisions for concurrent MCP requests.
"""

import asyncio
import uuid
import logging

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Literal
logger = logging.getLogger(__name__)

DecisionMode = Literal["manual", "allow", "block"]


@dataclass
class ApprovalRequest:
    request_id: str
    server_name: str
    tool_name: str
    arguments: dict[str, Any]
    created_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )


class ApprovalManager:
    def __init__(
        self,
        mode: DecisionMode = "manual",
        timeout: float = 120.0,
        test_decision_delay: float = 0.5,
    ):
        self.mode = mode
        self.timeout = timeout
        self.test_decision_delay = test_decision_delay

        self._pending: dict[
            str, tuple[ApprovalRequest, asyncio.Future[bool]]
        ] = {}

        self._loop: asyncio.AbstractEventLoop | None = None

    async def request_approval(
        self,
        server_name: str,
        tool_name: str,
        arguments: dict[str, Any],
    ) -> bool:
        """Create an independent approval request and wait for a decision."""

        loop = asyncio.get_running_loop()
        self._loop = loop

        request_id = str(uuid.uuid4())

        request = ApprovalRequest(
            request_id=request_id,
            server_name=server_name,
            tool_name=tool_name,
            arguments=arguments,
        )

        future: asyncio.Future[bool] = loop.create_future()

        self._pending[request_id] = (request, future)

        logger.info("Pending approval: %s | ID: %s", tool_name, request_id)

        try:
            # Deterministic modes are only for integration testing.
            if self.mode in ("allow", "block"):
                await asyncio.sleep(self.test_decision_delay)

                self.decide(
                    request_id,
                    allowed=(self.mode == "allow"),
                )

            # Shield prevents wait_for from cancelling the decision future.
            return await asyncio.wait_for(
                asyncio.shield(future),
                timeout=self.timeout,
            )

        except asyncio.TimeoutError:
            logger.warning("Approval timed out. Blocking %s.", tool_name)
            return False

        except asyncio.CancelledError:
            # Cancellation must never become approval.
            raise

        finally:
            self._pending.pop(request_id, None)

            if not future.done():
                future.cancel()

    def decide(self, request_id: str, allowed: bool) -> None:
        """
        Submit a decision.

        call_soon_threadsafe allows the future Qt UI to submit decisions
        from its GUI thread.
        """

        loop = self._loop

        if loop is None or loop.is_closed():
            return

        loop.call_soon_threadsafe(
            self._resolve_decision,
            request_id,
            allowed,
        )

    def _resolve_decision(
        self,
        request_id: str,
        allowed: bool,
    ) -> None:
        pending = self._pending.get(request_id)

        if pending is None:
            return

        _, future = pending

        # First decision wins.
        if not future.done():
            future.set_result(allowed)

            decision = "ALLOW" if allowed else "BLOCK"
            logger.info("Decision: %s | ID: %s", decision, request_id)

    @property
    def pending_requests(self) -> list[ApprovalRequest]:
        """Return a snapshot for the future desktop interface."""

        return [
            request
            for request, _ in self._pending.values()
        ]
