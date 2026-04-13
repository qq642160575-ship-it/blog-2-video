from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator


class ScriptSegment(BaseModel):
    segment_id: str
    text: str
    role: str
    importance: int = Field(default=3, ge=1, le=5)


class ParsedScript(BaseModel):
    source_id: str = "source"
    intent: str
    tone: str
    emotion_curve: list[str] = Field(default_factory=list)
    segments: list[ScriptSegment] = Field(default_factory=list)


class OralScriptResult(BaseModel):
    source_text: str
    oral_script: str
    script_segments: list[ScriptSegment] = Field(default_factory=list)
    script_metadata: dict[str, Any] = Field(default_factory=dict)
    review_score: int | None = None
    feedback: str | None = None


class ScenePlan(BaseModel):
    scene_id: str
    type: str
    start: int = 0
    end: int = 0
    duration_in_frames: int = 0
    text: str
    segment_id: str | None = None
    narrative_role: str
    visual_goal: str
    layout_slots: list[str] = Field(default_factory=list)
    motion_profile: str = "soft_focus_in"
    priority: int = Field(default=3, ge=1, le=5)


class MarksBundle(BaseModel):
    fps: int = 30
    duration_in_frames: int = 0
    global_marks: dict[str, int] = Field(default_factory=dict)
    scene_marks: dict[str, dict[str, int]] = Field(default_factory=dict)


class SafeArea(BaseModel):
    x: int = 84
    y: int = 120
    width: int = 912
    height: int = 1680


class CanvasSpec(BaseModel):
    width: int = 1080
    height: int = 1920
    safe_area: SafeArea = Field(default_factory=SafeArea)


class LayoutNode(BaseModel):
    id: str
    kind: str
    box: dict[str, int]
    z_index: int = 1
    props: dict[str, Any] = Field(default_factory=dict)


class LayoutSpec(BaseModel):
    scene_id: str
    canvas: CanvasSpec = Field(default_factory=CanvasSpec)
    nodes: list[LayoutNode] = Field(default_factory=list)


class MotionItem(BaseModel):
    target: str
    entry: str
    start: int
    end: int
    params: dict[str, Any] = Field(default_factory=dict)


class MotionSpec(BaseModel):
    scene_id: str
    motions: list[MotionItem] = Field(default_factory=list)


class DSLNode(BaseModel):
    type: str
    props: dict[str, Any] = Field(default_factory=dict)
    children: list["DSLNode"] = Field(default_factory=list)


class RemotionDSL(BaseModel):
    scene_id: str
    component_tree: DSLNode


class SceneCode(BaseModel):
    scene_id: str
    component_name: str
    code: str


class ValidationErrorItem(BaseModel):
    code: str
    message: str | None = None
    scene_id: str | None = None
    node_id: str | None = None
    stage: str | None = None


class ValidationResult(BaseModel):
    scene_id: str
    status: Literal["pass", "warning", "fail"]
    stage: str
    repairable: bool = False
    errors: list[ValidationErrorItem] = Field(default_factory=list)


class PatchOp(BaseModel):
    op: Literal["replace", "add", "remove"]
    path: str
    value: Any | None = None


class ScenePatch(BaseModel):
    target: str | None = None
    patch_type: str
    ops: list[PatchOp] = Field(default_factory=list)

    @field_validator("ops")
    @classmethod
    def ensure_non_empty(cls, value: list[PatchOp]) -> list[PatchOp]:
        if not value:
            raise ValueError("Patch operations cannot be empty")
        return value
