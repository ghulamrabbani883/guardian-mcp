
import asyncio

import pytest

from app.approval.manager import ApprovalManager


async def wait_for_pending(manager, expected_count):
    async def check():
        while len(manager.pending_requests) != expected_count:
            await asyncio.sleep(0.005)

    await asyncio.wait_for(check(), timeout=2.0)


@pytest.mark.asyncio
async def test_concurrent_requests_have_independent_decisions():

    manager = ApprovalManager(
        mode="manual",
        timeout=5,
    )

    request_a = asyncio.create_task(
        manager.request_approval(
            "server-a",
            "add_numbers",
            {"a": 10, "b": 20},
        )
    )

    request_b = asyncio.create_task(
        manager.request_approval(
            "server-b",
            "get_server_status",
            {},
        )
    )

    request_c = asyncio.create_task(
        manager.request_approval(
            "server-a",
            "add_numbers",
            {"a": 5, "b": 8},
        )
    )

    await wait_for_pending(manager, 3)

    pending = manager.pending_requests

    # Identify requests using their actual arguments,
    # rather than assuming tool names are unique.

    id_a = next(
        request.request_id
        for request in pending
        if request.server_name == "server-a"
        and request.arguments.get("a") == 10
    )

    id_b = next(
        request.request_id
        for request in pending
        if request.server_name == "server-b"
    )

    id_c = next(
        request.request_id
        for request in pending
        if request.server_name == "server-a"
        and request.arguments.get("a") == 5
    )

    # Verify that all three IDs are independent.
    assert len({id_a, id_b, id_c}) == 3

    # Deliberately decide in a different order.
    manager.decide(id_b, False)
    manager.decide(id_c, True)
    manager.decide(id_a, True)

    results = await asyncio.gather(
        request_a,
        request_b,
        request_c,
    )

    assert results == [True, False, True]

    assert manager.pending_requests == []


@pytest.mark.asyncio
async def test_concurrent_timeout_does_not_affect_approved_request():

    manager = ApprovalManager(
        mode="manual",
        timeout=0.1,
    )

    approved_task = asyncio.create_task(
        manager.request_approval(
            "server-a",
            "add_numbers",
            {"a": 1, "b": 2},
        )
    )

    timeout_task = asyncio.create_task(
        manager.request_approval(
            "server-b",
            "get_server_status",
            {},
        )
    )

    await wait_for_pending(manager, 2)

    approved_request = next(
        request
        for request in manager.pending_requests
        if request.server_name == "server-a"
    )

    manager.decide(
        approved_request.request_id,
        True,
    )

    approved, timed_out = await asyncio.gather(
        approved_task,
        timeout_task,
    )

    assert approved is True
    assert timed_out is False

    assert manager.pending_requests == []
