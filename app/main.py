
"""
MCP Guardian - Application Entry Point
"""

import argparse
import asyncio
import logging
import sys

from pathlib import Path

from app.approval.manager import ApprovalManager
from app.core.config import load_config
from app.core.logging import configure_logging
from app.gateway.proxy import run_proxy
from app.remote.server import run_remote_gateway


def parse_arguments():

    parser = argparse.ArgumentParser(
        description="MCP Guardian - MCP Security Gateway"
    )

    parser.add_argument(
        "--approval-mode",
        choices=["manual", "allow", "block"],
        default="manual",
    )

    parser.add_argument(
        "--approval-timeout",
        type=float,
        default=120.0,
    )

    parser.add_argument(
        "--config",
        type=str,
        default=None,
        help="Path to a JSON Guardian configuration file.",
    )

    parser.add_argument(
        "--transport",
        choices=["stdio", "remote"],
        default=None,
        help="stdio for Claude Desktop; remote for Streamable HTTP connectors.",
    )

    parser.add_argument(
        "--host",
        default=None,
        help="Remote gateway bind host.",
    )

    parser.add_argument(
        "--port",
        type=int,
        default=None,
        help="Remote gateway bind port.",
    )

    parser.add_argument(
        "--remote-path",
        default=None,
        help="Remote MCP endpoint path.",
    )

    parser.add_argument(
        "--bearer-token",
        default=None,
        help="Bearer token required by the remote MCP gateway.",
    )

    return parser.parse_args()


def get_upstream_server(config):
    if config.upstream_args:
        return config

    project_root = Path(__file__).resolve().parents[1]
    server_path = project_root / "examples" / "sample_mcp_server.py"
    if not server_path.exists():
        raise FileNotFoundError(
            f"Sample MCP server not found: {server_path}"
        )

    config.upstream_args = [str(server_path)]
    return config


def run_headless(args, config):
    approval_mode = args.approval_mode
    approval_timeout = args.approval_timeout

    if args.approval_mode == "manual":
        approval_mode = config.approval_mode
    if args.approval_timeout == 120.0:
        approval_timeout = config.approval_timeout

    if config.transport == "remote":
        asyncio.run(
            run_remote_gateway(
                upstream_command=config.upstream_command,
                upstream_args=config.upstream_args,
                approval_manager=ApprovalManager(
                    mode=approval_mode,
                    timeout=approval_timeout,
                ),
                host=config.remote_host,
                port=config.remote_port,
                path=config.remote_path,
                bearer_token=config.bearer_token,
                upstream_name=config.upstream_name,
            )
        )
        return

    asyncio.run(
        run_proxy(
            upstream_command=config.upstream_command,
            upstream_args=config.upstream_args,
            approval_mode=approval_mode,
            approval_timeout=approval_timeout,
            upstream_name=config.upstream_name,
        )
    )


def run_desktop(args, config):

    from PySide6.QtWidgets import QApplication

    from app.desktop.bridge import ApprovalBridge
    from app.desktop.controller import GatewayController
    from app.desktop.tray import GuardianTray
    from app.desktop.window import GuardianWindow

    app = QApplication(sys.argv)

    app.setApplicationName("MCP Guardian")

    # Closing the main window must not terminate the gateway.
    app.setQuitOnLastWindowClosed(False)

    bridge = ApprovalBridge()

    approval_manager = ApprovalManager(
        mode="manual",
        timeout=(
            args.approval_timeout
            if args.approval_timeout != 120.0
            else config.approval_timeout
        ),
        on_request=bridge.request_created.emit,
    )

    if config.transport == "remote":
        if not config.bearer_token:
            raise ValueError(
                "Remote transport requires --bearer-token or bearer_token in JSON."
            )
        from app.remote.controller import RemoteGatewayController

        controller = RemoteGatewayController(
            approval_manager=approval_manager,
            bridge=bridge,
            upstream_command=config.upstream_command,
            upstream_args=config.upstream_args,
            host=config.remote_host,
            port=config.remote_port,
            path=config.remote_path,
            bearer_token=config.bearer_token,
            upstream_name=config.upstream_name,
        )
    else:
        controller = GatewayController(
            approval_manager=approval_manager,
            bridge=bridge,
            upstream_command=config.upstream_command,
            upstream_args=config.upstream_args,
        )

    window = GuardianWindow(
        bridge=bridge,
        approval_manager=approval_manager,
    )

    # Keep the tray object alive for the application's lifetime.
    tray = GuardianTray(app, window)

    controller.start()

    window.show()

    try:
        exit_code = app.exec()

    finally:
        controller.stop()

    return exit_code


def main():

    args = parse_arguments()

    configure_logging()

    config = load_config(args.config)
    config = get_upstream_server(config)

    if args.transport is not None:
        config.transport = args.transport
    if args.host is not None:
        config.remote_host = args.host
    if args.port is not None:
        config.remote_port = args.port
    if args.remote_path is not None:
        config.remote_path = args.remote_path
    if args.bearer_token is not None:
        config.bearer_token = args.bearer_token

    # Preserve the existing non-GUI modes.
    if args.approval_mode != "manual":
        run_headless(args, config)
        return

    # Manual approval mode runs with the desktop UI.
    exit_code = run_desktop(args, config)

    sys.exit(exit_code)


if __name__ == "__main__":

    try:
        main()

    except KeyboardInterrupt:
        logging.info("MCP Guardian interrupted.")

    except Exception:
        logging.exception(
            "MCP Guardian terminated unexpectedly."
        )
        raise
