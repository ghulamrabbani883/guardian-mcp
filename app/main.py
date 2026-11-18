
"""
MCP Guardian - Application Entry Point
"""

import argparse
import asyncio
import logging
import sys

from pathlib import Path

from app.approval.manager import ApprovalManager
from app.core.logging import configure_logging
from app.gateway.proxy import run_proxy


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

    return parser.parse_args()


def get_upstream_server():

    project_root = Path(__file__).resolve().parents[1]

    server_path = (
        project_root
        / "examples"
        / "sample_mcp_server.py"
    )

    if not server_path.exists():
        raise FileNotFoundError(
            f"Sample MCP server not found: {server_path}"
        )

    return server_path


def main():

    args = parse_arguments()

    configure_logging()

    upstream_server = get_upstream_server()

    # Preserve existing headless integration-test modes.
    if args.approval_mode != "manual":

        asyncio.run(
            run_proxy(
                upstream_command=sys.executable,
                upstream_args=[str(upstream_server)],
                approval_mode=args.approval_mode,
                approval_timeout=args.approval_timeout,
            )
        )

        return

    # Desktop mode.
    from PySide6.QtWidgets import QApplication

    from app.desktop.bridge import ApprovalBridge
    from app.desktop.controller import GatewayController
    from app.desktop.window import GuardianWindow

    app = QApplication(sys.argv)

    app.setApplicationName("MCP Guardian")
    app.setQuitOnLastWindowClosed(False)

    bridge = ApprovalBridge()

    approval_manager = ApprovalManager(
        mode="manual",
        timeout=args.approval_timeout,
        on_request=bridge.request_created.emit,
    )

    controller = GatewayController(
        approval_manager=approval_manager,
        bridge=bridge,
        upstream_command=sys.executable,
        upstream_args=[str(upstream_server)],
    )

    window = GuardianWindow(
        bridge=bridge,
        approval_manager=approval_manager,
    )

    controller.start()

    window.show()

    try:
        exit_code = app.exec()
    finally:
        controller.stop()

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
