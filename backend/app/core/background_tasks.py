"""Strong-reference background task helper.

``asyncio.ensure_future`` is deprecated in favor of ``asyncio.create_task``
in 3.10+. Both have the same load-bearing foot-gun: if the only reference
to the task is the call expression, the garbage collector can reclaim the
task before it finishes — silently — leading to "fire-and-forget" tasks
that vanish at random.

The fix is to keep a strong reference in a long-lived set and remove it
when the task completes. This module provides one shared helper used by
the API handlers that spawn inline crew runs.

Also adds a done-callback that logs any uncaught exception. Without it,
a crashed background task is invisible.
"""
from __future__ import annotations

import asyncio
import logging
from typing import Coroutine

logger = logging.getLogger(__name__)

# Module-level strong reference set. Tasks remove themselves from this set
# in a done-callback so the set doesn't grow unbounded.
_background_tasks: set[asyncio.Task] = set()


def spawn_background_task(coro: Coroutine, name: str | None = None) -> asyncio.Task:
    """Run ``coro`` in the background with the GC-safety + logging guarantees.

    Callers MUST be inside a running event loop (any ``async def`` body).
    """
    task = asyncio.create_task(coro, name=name)
    _background_tasks.add(task)
    task.add_done_callback(_on_done)
    return task


def _on_done(task: asyncio.Task) -> None:
    _background_tasks.discard(task)
    if task.cancelled():
        return
    exc = task.exception()
    if exc is not None:
        logger.exception(
            "Background task %s raised", task.get_name(), exc_info=exc
        )
