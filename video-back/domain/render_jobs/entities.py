from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class RenderJobRecord(BaseModel):
    """渲染任务记录"""

    job_id: str
    scene_artifact_id: str
    scene_id: str
    status: str  # "pending", "rendering", "validating", "completed", "failed"
    frame: int = 0
    storage_url: str | None = None
    render_time_ms: float | None = None
    validation_passed: bool | None = None
    validation_issues: list[dict[str, Any]] = Field(default_factory=list)
    error_message: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
