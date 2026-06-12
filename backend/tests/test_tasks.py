import asyncio

import pytest

from app.tasks import background_task_count, spawn


@pytest.mark.asyncio
async def test_spawn_logs_exception(caplog):
    async def boom():
        raise ValueError("task failed")

    task = spawn(boom())
    for _ in range(50):
        if task.done():
            break
        await asyncio.sleep(0.01)
    assert task.done()
    assert background_task_count() == 0
    assert any("task failed" in r.message or "background task failed" in r.message for r in caplog.records)


@pytest.mark.asyncio
async def test_spawn_many_noop():
    async def noop():
        return None

    tasks = [spawn(noop()) for _ in range(100)]
    await asyncio.gather(*tasks)
    assert background_task_count() == 0
