import asyncio

import pytest
from solver.util import ZeroBarrier


@pytest.mark.asyncio
async def test_zero_barrier():
    barrier = ZeroBarrier()

    # initial state
    assert barrier._pending == 0
    assert not barrier._event.is_set()

    # push increments _pending and clears _event
    barrier.push()
    assert barrier._pending == 1
    assert not barrier._event.is_set()

    # pop decrements _pending; _event is set when _pending is 0
    barrier.pop()
    assert barrier._pending == 0
    assert barrier._event.is_set()

    # test wait: ensure it blocks when _pending > 0
    async def task():
        await asyncio.sleep(0.1)
        barrier.pop()

    barrier.push()
    task_future = asyncio.create_task(task())
    await barrier.wait()
    assert barrier._pending == 0
    assert barrier._event.is_set()
    await task_future


@pytest.mark.asyncio
async def test_concurrent_waiters():
    barrier = ZeroBarrier()

    # start with some pending tasks
    barrier.push()
    barrier.push()

    # define tasks that wait for barrier
    results = []

    async def waiting_task(idx):
        await barrier.wait()
        results.append(idx)

    tasks = [asyncio.create_task(waiting_task(i)) for i in range(3)]

    # allow time for all tasks to start waiting
    await asyncio.sleep(0.1)
    assert len(results) == 0  # no task should finish yet

    # pop until barrier is open
    barrier.pop()
    assert len(results) == 0  # still waiting
    barrier.pop()

    # wait for all tasks to finish
    await asyncio.gather(*tasks)
    assert len(results) == 3
    assert sorted(results) == [0, 1, 2]
