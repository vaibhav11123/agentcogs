"""Background task registry — keeps references so CPython does not GC pending work."""
from __future__ import annotations

import asyncio
import logging

log = logging.getLogger("agentcogs.tasks")

_background_tasks: set[asyncio.Task] = set()


def spawn(coro) -> asyncio.Task:
    task = asyncio.create_task(coro)
    _background_tasks.add(task)

    def _done(t: asyncio.Task) -> None:
        _background_tasks.discard(t)
        if t.cancelled():
            return
        exc = t.exception()
        if exc is not None:
            log.error("background task failed", exc_info=exc)

    task.add_done_callback(_done)
    return task


def background_task_count() -> int:
    return len(_background_tasks)
