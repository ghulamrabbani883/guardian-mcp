import asyncio
from contextlib import asynccontextmanager
from types import SimpleNamespace

import pytest

from app.approval.manager import ApprovalManager
from app.gateway.proxy import discover_upstream_tools, run_proxy


class FakeUpstreamSession:
    def __init__(self):
        self.calls = []
        self.pages = {
            None: SimpleNamespace(
                tools=[
                    SimpleNamespace(name="add_numbers", description="Add"),
                ],
                nextCursor="next-page",
            ),
            "next-page": SimpleNamespace(
                tools=[
                    SimpleNamespace(name="get_status", description="Status"),
                ],
                nextCursor=None,
            ),
        }

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, traceback):
        return False

    async def initialize(self):
        return SimpleNamespace()

    async def list_tools(self, cursor=None):
        return self.pages[cursor]

    async def call_tool(self, name, arguments):
        self.calls.append((name, arguments))
        return SimpleNamespace(
            isError=False,
            content=[
                SimpleNamespace(
                    text=f"executed:{name}:{arguments}",
                )
            ],
        )


@pytest.mark.asyncio
async def test_discover_upstream_tools_reads_all_pages():
    upstream = FakeUpstreamSession()

    tools = await discover_upstream_tools(upstream)

    assert [tool.name for tool in tools] == [
        "add_numbers",
        "get_status",
    ]


class FakeDownstreamServer:
    def __init__(self, name, version=None, instructions=None):
        self.call_handler = None
        self.list_handler = None

    def list_tools(self):
        def decorator(handler):
            self.list_handler = handler
            return handler

        return decorator

    def call_tool(self):
        def decorator(handler):
            self.call_handler = handler
            return handler

        return decorator

    def create_initialization_options(self):
        return SimpleNamespace()

    async def run(self, read_stream, write_stream, options):
        await asyncio.sleep(0)


@asynccontextmanager
async def fake_stdio_client(parameters):
    yield object(), object()


@asynccontextmanager
async def fake_stdio_server():
    yield object(), object()


@pytest.mark.asyncio
async def test_proxy_forward_blocked_call_never_reaches_upstream(monkeypatch):
    upstream = FakeUpstreamSession()
    downstream_servers = []

    monkeypatch.setattr(
        "app.gateway.proxy.stdio_client",
        fake_stdio_client,
    )
    monkeypatch.setattr(
        "app.gateway.proxy.stdio_server",
        fake_stdio_server,
    )
    monkeypatch.setattr(
        "app.gateway.proxy.ClientSession",
        lambda read, write: upstream,
    )
    monkeypatch.setattr(
        "app.gateway.proxy.Server",
        lambda *args, **kwargs: downstream_servers.append(
            FakeDownstreamServer(*args, **kwargs)
        )
        or downstream_servers[-1],
    )

    manager = ApprovalManager(mode="block", timeout=1)

    await run_proxy(
        upstream_command="unused",
        upstream_args=[],
        approval_manager=manager,
    )

    server = downstream_servers[0]
    with pytest.raises(Exception, match="Guardian blocked"):
        await server.call_handler(
            "add_numbers",
            {"a": 10, "b": 20},
        )

    assert upstream.calls == []


@pytest.mark.asyncio
async def test_proxy_forwards_approved_call_and_arguments(monkeypatch):
    upstream = FakeUpstreamSession()
    downstream_servers = []

    monkeypatch.setattr(
        "app.gateway.proxy.stdio_client",
        fake_stdio_client,
    )
    monkeypatch.setattr(
        "app.gateway.proxy.stdio_server",
        fake_stdio_server,
    )
    monkeypatch.setattr(
        "app.gateway.proxy.ClientSession",
        lambda read, write: upstream,
    )
    monkeypatch.setattr(
        "app.gateway.proxy.Server",
        lambda *args, **kwargs: downstream_servers.append(
            FakeDownstreamServer(*args, **kwargs)
        )
        or downstream_servers[-1],
    )

    manager = ApprovalManager(mode="allow", timeout=1)

    await run_proxy(
        upstream_command="unused",
        upstream_args=[],
        approval_manager=manager,
    )

    server = downstream_servers[0]
    content = await server.call_handler(
        "add_numbers",
        {"a": 10, "b": 20},
    )

    assert upstream.calls == [
        ("add_numbers", {"a": 10, "b": 20}),
    ]
    assert content[0].text.startswith("executed:add_numbers:")


@pytest.mark.asyncio
async def test_proxy_rejects_unknown_tool(monkeypatch):
    upstream = FakeUpstreamSession()
    downstream_servers = []

    monkeypatch.setattr(
        "app.gateway.proxy.stdio_client",
        fake_stdio_client,
    )
    monkeypatch.setattr(
        "app.gateway.proxy.stdio_server",
        fake_stdio_server,
    )
    monkeypatch.setattr(
        "app.gateway.proxy.ClientSession",
        lambda read, write: upstream,
    )
    monkeypatch.setattr(
        "app.gateway.proxy.Server",
        lambda *args, **kwargs: downstream_servers.append(
            FakeDownstreamServer(*args, **kwargs)
        )
        or downstream_servers[-1],
    )

    manager = ApprovalManager(mode="allow", timeout=1)

    await run_proxy(
        upstream_command="unused",
        upstream_args=[],
        approval_manager=manager,
    )

    server = downstream_servers[0]
    with pytest.raises(ValueError, match="Unknown upstream tool"):
        await server.call_handler(
            "delete_everything",
            {},
        )

    assert upstream.calls == []

