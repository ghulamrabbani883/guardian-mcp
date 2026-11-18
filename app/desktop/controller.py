"""
MCP Guardian - Background Gateway Controller

Runs the asyncio MCP gateway on a dedicated worker thread,
while Qt owns the main application thread.
"""

import asyncio
import logging
import threading

from app.approval.manager import ApprovalManager
from app.desktop.bridge import ApprovalBridge
from app.gateway.proxy import run_proxy

logger = logging.getLogger(__name__)


class GatewayController:

    def __init__(
        self,
        approval_manager: ApprovalManager,
        bridge: ApprovalBridge,
        upstream_command: str,
        upstream_args: list[str],
    ):
        self.approval_manager = approval_manager
        self.bridge = bridge

        self.upstream_command = upstream_command
        self.upstream_args = upstream_args

        self.stop_event = threading.Event()

        self.thread = threading.Thread(
            target=self._run,
            name="mcp-guardian-gateway",
            daemon=True,
        )

    def start(self):
        self.thread.start()

    def _run(self):
        try:
            asyncio.run(self._run_async())

        except Exception as exc:
            logger.exception("Gateway stopped unexpectedly")
            self.bridge.gateway_error.emit(str(exc))

        finally:
            self.bridge.gateway_status.emit("Stopped")

    async def _run_async(self):
        self.bridge.gateway_status.emit("Running")

        gateway_task = asyncio.create_task(
            run_proxy(
                upstream_command=self.upstream_command,
                upstream_args=self.upstream_args,
                approval_manager=self.approval_manager,
            ),
            name="mcp-guardian-proxy",
        )

        stop_task = asyncio.create_task(
            asyncio.to_thread(self.stop_event.wait),
            name="mcp-guardian-stop-watcher",
        )

        try:
            done, _ = await asyncio.wait(
                {gateway_task, stop_task},
                return_when=asyncio.FIRST_COMPLETED,
            )

            if stop_task in done:
                logger.info("Shutdown requested")

                gateway_task.cancel()

                try:
                    await asyncio.wait_for(
                        asyncio.gather(
                            gateway_task,
                            return_exceptions=True,
                        ),
                        timeout=5,
                    )
                except asyncio.TimeoutError:
                    logger.error(
                        "Gateway cancellation timed out."
                    )

            else:
                # Gateway ended independently.
                self.stop_event.set()

                await gateway_task

        finally:
            if not stop_task.done():
                stop_task.cancel()

                await asyncio.gather(
                    stop_task,
                    return_exceptions=True,
                )

    def stop(self):
        logger.info("Stopping MCP Guardian")

        self.stop_event.set()

        if self.thread.is_alive():
            self.thread.join(timeout=7)

        if self.thread.is_alive():
            logger.error(
                "Gateway thread did not stop within 7 seconds"
            )