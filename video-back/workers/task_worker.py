from __future__ import annotations

import asyncio

from infra.queue.inline_queue import InlineTaskQueue
from orchestration.task_runner import TaskRunner


class TaskWorker:
    def __init__(self, queue: InlineTaskQueue, runner: TaskRunner) -> None:
        self.queue = queue
        self.runner = runner
        self._stopped = asyncio.Event()

    async def run_forever(self) -> None:
        while not self._stopped.is_set():
            task_id = await self.queue.dequeue()
            if not task_id:
                await asyncio.sleep(0.05)
                continue
            await self.runner.run(task_id)

    async def stop(self) -> None:
        self._stopped.set()
