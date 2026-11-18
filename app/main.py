
"""
MCP Guardian - Application Entry Point
"""

import argparse
import asyncio
import logging
import sys

from pathlib import Path

from app.core.logging import configure_logging
from app.gateway.proxy import run_proxy


def parse_arguments():
    parser = argparse.ArgumentParser(
        description="MCP Guardian - MCP request interception gateway"
    )

    parser.add_argument(
        "--approval-mode",
        choices=["manual", "allow", "block"],
        default="manual",
        help="Manual approval or deterministic integration-test mode.",
    )

    parser.add_argument(
        "--approval-timeout",
        type=float,
        default=120.0,
    )

    return parser.parse_args()


async def main():
    args = parse_arguments()

    configure_logging()

    project_root = Path(__file__).resolve().parents[1]

    upstream_server = (
        project_root / "examples" / "sample_mcp_server.py"
    )

    if not upstream_server.exists():
        raise FileNotFoundError(
            f"Sample MCP server not found: {upstream_server}"
        )

    logging.info("Starting MCP Guardian")

    await run_proxy(
        upstream_command=sys.executable,
        upstream_args=[str(upstream_server)],
        approval_mode=args.approval_mode,
        approval_timeout=args.approval_timeout,
    )


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info("MCP Guardian shutting down.")
    except Exception:
        logging.exception("MCP Guardian terminated unexpectedly.")
        raise
