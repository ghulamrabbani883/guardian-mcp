
"""
MCP Guardian - End-to-End Integration Test Client

Starts Guardian as a subprocess and connects through MCP stdio.
"""

import argparse
import asyncio
import sys

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def main(decision: str):
    guardian_params = StdioServerParameters(
        command=sys.executable,
        args=[
            "-m",
            "app.main",
            "--approval-mode",
            decision,
        ],
    )

    async with stdio_client(guardian_params) as (
        read_stream,
        write_stream,
    ):
        async with ClientSession(
            read_stream,
            write_stream,
        ) as session:

            await session.initialize()

            print("\nConnected to MCP Guardian.")

            tools = await session.list_tools()

            print("\nTools exposed by Guardian:")

            for tool in tools.tools:
                print(f"- {tool.name}: {tool.description}")

            print("\nInvoking add_numbers(10, 20)...")

            result = await session.call_tool(
                "add_numbers",
                {"a": 10, "b": 20},
            )

            print("\nMCP response:")
            print("isError:", result.isError)

            for item in result.content:
                if hasattr(item, "text"):
                    print(item.text)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--decision",
        choices=["allow", "block", "manual"],
        required=True,
    )

    args = parser.parse_args()

    asyncio.run(main(args.decision))
