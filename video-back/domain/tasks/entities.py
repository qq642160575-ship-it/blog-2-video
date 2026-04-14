from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field

from domain.common.enums import TaskStatus, TaskType
from domain.common.ids import new_id


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class TaskRecord(BaseModel):
    id: str = Field(default_factory=lambda: new_id("task"))
    session_id: str
    branch_id: str
    task_type: TaskType
    status: TaskStatus = TaskStatus.PENDING
    priority: int = 100
    requested_by: str | None = None
    request_payload: dict[str, Any] = Field(default_factory=dict)
    baseline_artifact_id: str | None = None
    result_summary: dict[str, Any] = Field(default_factory=dict)
    error_code: str | None = None
    error_message: str | None = None
    cancellation_requested: bool = False
    created_at: datetime = Field(default_factory=utcnow)
    started_at: datetime | None = None
    finished_at: datetime | None = None


class TaskRunRecord(BaseModel):
    id: str = Field(default_factory=lambda: new_id("run"))
    task_id: str
    attempt: int = 1
    status: TaskStatus = TaskStatus.RUNNING
    created_at: datetime = Field(default_factory=utcnow)
