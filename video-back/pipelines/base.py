from __future__ import annotations

from typing import Protocol

from orchestration.task_context import PipelineResult, TaskContext


class Pipeline(Protocol):
    name: str

    async def run(self, context: TaskContext) -> PipelineResult:
        ...
