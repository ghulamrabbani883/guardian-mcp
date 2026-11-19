"""Qt controller for the remote Streamable HTTP gateway."""

import asyncio
import logging
import threading

from app.approval.manager import ApprovalManager
from app.desktop.bridge import ApprovalBridge
from app.remote.server import run_remote_gateway


logger = logging.getLogger(__name__)


class RemoteGatewayController:
    def __init__(
        self,
        approval_manager: ApprovalManager,
        bridge: ApprovalBridge,
        upstream_command: str,
        upstream_args: list[str],
        host: str,
        port: int,
        path: str,
        bearer_token: str,
        upstream_name: str,
    ):
        self.approval_manager = approval_manager
        self.bridge = bridge
        self.upstream_command = upstream_command
        self.upstream_args = upstream_args
        self.host = host
        self.port = port
        self.path = path
        self.bearer_token = bearer_token
        self.upstream_name = upstream_name
        self.stop_event = threading.Event()
        self.thread = threading.Thread(
            target=self._run,
            name="mcp-guardian-remote-gateway",
            daemon=True,
        )

    def start(self) -> None:
        self.thread.start()

    def _run(self) -> None:
        try:
            asyncio.run(self._run_async())
        except Exception as exc:
            logger.exception("Remote gateway stopped unexpectedly")
            self.bridge.gateway_error.emit(str(exc))
        finally:
            self.bridge.gateway_status.emit("Stopped")

    async def _run_async(self) -> None:
        self.bridge.gateway_status.emit("Running")
        gateway_task = asyncio.create_task(
            run_remote_gateway(
                upstream_command=self.upstream_command,
                upstream_args=self.upstream_args,
                approval_manager=self.approval_manager,
                host=self.host,
                port=self.port,
                path=self.path,
                bearer_token=self.bearer_token,
                upstream_name=self.upstream_name,
            )
        )
        stop_task = asyncio.create_task(
            asyncio.to_thread(self.stop_event.wait)
        )

        done, _ = await asyncio.wait(
            {gateway_task, stop_task},
            return_when=asyncio.FIRST_COMPLETED,
        )

        if stop_task in done:
            gateway_task.cancel()
            await asyncio.gather(gateway_task, return_exceptions=True)
        else:
            await gateway_task

    def stop(self) -> None:
        self.stop_event.set()
