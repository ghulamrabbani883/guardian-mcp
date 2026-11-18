
import pytest

from app.approval.manager import ApprovalManager
from app.gateway.interceptor import (
    ToolBlockedError,
    ToolInterceptor,
)


@pytest.mark.asyncio
async def test_interceptor_allows_approved_request():
    manager = ApprovalManager(mode="allow")

    interceptor = ToolInterceptor(
        approval_manager=manager,
        server_name="test-server",
    )

    await interceptor.authorize(
        "add_numbers",
        {"a": 10, "b": 20},
    )


@pytest.mark.asyncio
async def test_interceptor_rejects_blocked_request():
    manager = ApprovalManager(mode="block")

    interceptor = ToolInterceptor(
        approval_manager=manager,
        server_name="test-server",
    )

    with pytest.raises(ToolBlockedError):
        await interceptor.authorize(
            "add_numbers",
            {"a": 10, "b": 20},
        )
