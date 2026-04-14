from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field

from domain.common.enums import SessionStatus
from domain.common.ids import new_id


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class SessionRecord(BaseModel):
    id: str = Field(default_factory=lambda: new_id("sess"))
    user_id: str | None = None
    title: str | None = None
    source_type: str
    source_content: str
    status: SessionStatus = SessionStatus.ACTIVE
    current_branch_id: str | None = None
    user_preference: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)


class BranchRecord(BaseModel):
    id: str = Field(default_factory=lambda: new_id("br"))
    session_id: str
    parent_branch_id: str | None = None
    base_artifact_id: str | None = None
    name: str = "main"
    head_artifact_id: str | None = None
    version: int = 1
    created_from_task_id: str | None = None
    created_at: datetime = Field(default_factory=utcnow)
