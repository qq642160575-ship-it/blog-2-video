from __future__ import annotations

import asyncio


class InlineTaskQueue:
    def __init__(self) -> None:
        self._queue: asyncio.Queue[str] = asyncio.Queue()

    async def enqueue(self, task_id: str, priority: int = 100) -> None:
        await self._queue.put(task_id)

    async def dequeue(self) -> str | None:
        return await self._queue.get()
