from typing import Any

from pydantic import BaseModel

from domain.common.enums import ArtifactType, SessionStatus, TaskStatus, TaskType


class GenerateRequest(BaseModel):
    source_text: str
    thread_id: str | None = None


class ReplayRequest(BaseModel):
    thread_id: str
    checkpoint_id: str


class ForkRequest(BaseModel):
    thread_id: str
    checkpoint_id: str
    values: dict[str, Any] | None = None
    as_node: str | None = None


class RegenerateSceneRequest(BaseModel):
    thread_id: str
    scene_id: str
    script: str
    visual_design: str


class UserPreference(BaseModel):
    style_family: str | None = None
    duration_seconds: int | None = None


class CreateSessionRequest(BaseModel):
    source_type: str
    source_content: str
    title: str | None = None
    user_preference: UserPreference | None = None


class CreateSessionResponse(BaseModel):
    session_id: str
    branch_id: str
    status: SessionStatus


class SessionOverviewResponse(BaseModel):
    session_id: str
    title: str | None
    source_type: str
    status: SessionStatus
    current_branch_id: str | None


class CreateTaskRequest(BaseModel):
    branch_id: str
    task_type: TaskType
    request_payload: dict[str, Any]
    baseline_artifact_id: str | None = None


class CreateTaskResponse(BaseModel):
    task_id: str
    status: TaskStatus


class BranchResponse(BaseModel):
    branch_id: str
    session_id: str
    parent_branch_id: str | None
    base_artifact_id: str | None
    head_artifact_id: str | None
    version: int


class ArtifactResponse(BaseModel):
    artifact_id: str
    session_id: str
    branch_id: str
    task_id: str | None
    artifact_type: ArtifactType
    artifact_subtype: str | None
    version: int
    content_json: dict[str, Any] | None
    content_text: str | None
    storage_url: str | None
    summary: str | None
    parent_artifact_id: str | None


class SceneArtifactResponse(BaseModel):
    scene_artifact_id: str
    artifact_id: str
    session_id: str
    branch_id: str
    scene_id: str
    scene_order: int
    scene_type: str | None
    script_text: str | None
    visual_intent: dict[str, Any] | None
    layout_spec: dict[str, Any] | None
    code_text: str | None
    validation_report: dict[str, Any] | None
    preview_image_url: str | None
    status: str
    version: int
