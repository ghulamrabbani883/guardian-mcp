
"""
MCP Guardian - Approval Manager

Manages independent approval requests and supports
thread-safe decisions from the desktop interface.
"""

import asyncio
import logging
import uuid

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Literal


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
        on_request: Callable[[ApprovalRequest], None] | None = None,
    ):
        self.mode = mode
        self.timeout = timeout
        self.test_decision_delay = test_decision_delay
        self.on_request = on_request

        self._pending: dict[
            str,
            tuple[ApprovalRequest, asyncio.Future[bool]],
        ] = {}

        self._loop: asyncio.AbstractEventLoop | None = None

    async def request_approval(
        self,
        server_name: str,
        tool_name: str,
        arguments: dict[str, Any],
    ) -> bool:

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

        logger.info(
            "Pending approval: %s | ID: %s",
            tool_name,
            request_id,
        )

        try:
            # Notify the desktop interface.
            if self.on_request is not None:
                self.on_request(request)

            # Deterministic modes are exclusively for testing.
            if self.mode in ("allow", "block"):
                await asyncio.sleep(self.test_decision_delay)

                self.decide(
                    request_id,
                    self.mode == "allow",
                )

            return await asyncio.wait_for(
                asyncio.shield(future),
                timeout=self.timeout,
            )

        except asyncio.TimeoutError:
            logger.warning(
                "Approval timed out. Blocking %s.",
                tool_name,
            )
            return False

        finally:
            self._pending.pop(request_id, None)

            if not future.done():
                future.cancel()

    def decide(
        self,
        request_id: str,
        allowed: bool,
    ) -> None:

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

        if not future.done():
            future.set_result(allowed)

            decision = "ALLOW" if allowed else "BLOCK"

            logger.info(
                "Decision: %s | ID: %s",
                decision,
                request_id,
            )

    @property
    def pending_requests(self) -> list[ApprovalRequest]:
        return [
            request
            for request, _ in self._pending.values()
        ]
