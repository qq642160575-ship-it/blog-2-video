from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Protocol
from uuid import uuid4

from pydantic import BaseModel, Field


class TaskEvent(BaseModel):
    id: str = Field(default_factory=lambda: f"evt_{uuid4().hex}")
    task_id: str
    task_run_id: str | None = None
    session_id: str
    branch_id: str
    scene_id: str | None = None
    event_type: str
    event_level: str = "info"
    node_key: str | None = None
    payload: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class TaskEventPublisher(Protocol):
    async def publish(
        self,
        event_type: str,
        *,
        task_id: str,
        session_id: str,
        branch_id: str,
        task_run_id: str | None = None,
        scene_id: str | None = None,
        event_level: str = "info",
        node_key: str | None = None,
        payload: dict[str, Any] | None = None,
    ) -> TaskEvent:
        ...


class InMemoryEventPublisher:
    def __init__(self) -> None:
        self.events: list[TaskEvent] = []

    async def publish(
        self,
        event_type: str,
        *,
        task_id: str,
        session_id: str,
        branch_id: str,
        task_run_id: str | None = None,
        scene_id: str | None = None,
        event_level: str = "info",
        node_key: str | None = None,
        payload: dict[str, Any] | None = None,
    ) -> TaskEvent:
        event = TaskEvent(
            task_id=task_id,
            task_run_id=task_run_id,
            session_id=session_id,
            branch_id=branch_id,
            scene_id=scene_id,
            event_type=event_type,
            event_level=event_level,
            node_key=node_key,
            payload=payload or {},
        )
        self.events.append(event)
        return event

    def list_by_task(self, task_id: str) -> list[TaskEvent]:
        return [event for event in self.events if event.task_id == task_id]
