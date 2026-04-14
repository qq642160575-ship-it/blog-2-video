from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field

from domain.common.enums import ArtifactType
from domain.common.ids import new_id


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class ArtifactRecord(BaseModel):
    id: str = Field(default_factory=lambda: new_id("art"))
    session_id: str
    branch_id: str
    task_id: str | None = None
    artifact_type: ArtifactType
    artifact_subtype: str | None = None
    version: int = 1
    content_json: dict[str, Any] | None = None
    content_text: str | None = None
    storage_url: str | None = None
    summary: str | None = None
    parent_artifact_id: str | None = None
    created_at: datetime = Field(default_factory=utcnow)


class SceneArtifactRecord(BaseModel):
    id: str = Field(default_factory=lambda: new_id("scnart"))
    artifact_id: str
    session_id: str
    branch_id: str
    scene_id: str
    scene_order: int
    scene_type: str | None = None
    script_text: str | None = None
    visual_intent: dict[str, Any] | None = None
    layout_spec: dict[str, Any] | None = None
    code_text: str | None = None
    validation_report: dict[str, Any] | None = None
    preview_image_url: str | None = None
    status: str = "ready"
    version: int = 1
    created_at: datetime = Field(default_factory=utcnow)
