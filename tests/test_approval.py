
import asyncio

import pytest

from app.approval.manager import ApprovalManager


async def wait_for_pending(manager, expected_count):
    """Wait until the expected number of requests are registered."""

    async def check():
        while len(manager.pending_requests) != expected_count:
            await asyncio.sleep(0.005)

    await asyncio.wait_for(check(), timeout=2.0)


@pytest.mark.asyncio
async def test_request_approved():
    manager = ApprovalManager(mode="allow")

    result = await manager.request_approval(
        "test-server",
        "add_numbers",
        {"a": 10, "b": 20},
    )

    assert result is True
    assert manager.pending_requests == []


@pytest.mark.asyncio
async def test_request_blocked():
    manager = ApprovalManager(mode="block")

    result = await manager.request_approval(
        "test-server",
        "add_numbers",
        {"a": 10, "b": 20},
    )

    assert result is False
    assert manager.pending_requests == []


@pytest.mark.asyncio
async def test_approval_timeout_fails_closed():
    manager = ApprovalManager(
        mode="manual",
        timeout=0.05,
    )

    result = await manager.request_approval(
        "test-server",
        "add_numbers",
        {"a": 10, "b": 20},
    )

    assert result is False
    assert manager.pending_requests == []


@pytest.mark.asyncio
async def test_duplicate_decisions_first_one_wins():
    manager = ApprovalManager(mode="manual")

    task = asyncio.create_task(
        manager.request_approval(
            "test-server",
            "add_numbers",
            {"a": 1, "b": 2},
        )
    )

    await wait_for_pending(manager, 1)

    request_id = manager.pending_requests[0].request_id

    manager.decide(request_id, True)
    manager.decide(request_id, False)

    result = await task

    assert result is True
    assert manager.pending_requests == []


@pytest.mark.asyncio
async def test_cancelled_request_is_cleaned_up():
    manager = ApprovalManager(mode="manual")

    task = asyncio.create_task(
        manager.request_approval(
            "test-server",
            "add_numbers",
            {"a": 1, "b": 2},
        )
    )

    await wait_for_pending(manager, 1)

    request_id = manager.pending_requests[0].request_id

    task.cancel()

    with pytest.raises(asyncio.CancelledError):
        await task

    assert manager.pending_requests == []

    # A late decision must not revive a cancelled request.
    manager.decide(request_id, True)

    await asyncio.sleep(0)

    assert manager.pending_requests == []
