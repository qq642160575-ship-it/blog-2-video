from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from domain.tasks.entities import TaskRecord, TaskRunRecord


class CancellationToken:
    def __init__(self, is_cancelled) -> None:
        self._is_cancelled = is_cancelled

    async def check(self) -> None:
        if await self._is_cancelled():
            raise TaskCancelledError("Task was cancelled")


class TaskCancelledError(Exception):
    pass


class TaskContext(BaseModel):
    task: TaskRecord
    run: TaskRunRecord
    request_payload: dict[str, Any] = Field(default_factory=dict)
    baseline_artifact_id: str | None = None
    cancellation_token: CancellationToken

    model_config = {"arbitrary_types_allowed": True}


class PipelineResult(BaseModel):
    summary: dict[str, Any] = Field(default_factory=dict)
    artifact_ids: list[str] = Field(default_factory=list)
    scene_artifact_ids: list[str] = Field(default_factory=list)
