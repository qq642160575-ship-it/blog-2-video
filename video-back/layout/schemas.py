from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator, model_validator


class CanvasSpec(BaseModel):
    width: int = 1080
    height: int = 1920
    safe_top: int = 96
    safe_right: int = 72
    safe_bottom: int = 120
    safe_left: int = 72

    @property
    def safe_x_min(self) -> int:
        return self.safe_left

    @property
    def safe_y_min(self) -> int:
        return self.safe_top

    @property
    def safe_x_max(self) -> int:
        return self.width - self.safe_right

    @property
    def safe_y_max(self) -> int:
        return self.height - self.safe_bottom


class LayoutBox(BaseModel):
    x: float
    y: float
    width: float
    height: float
    rotation: float = 0.0
    z_index: int = 0

    @field_validator("width", "height")
    @classmethod
    def validate_positive_size(cls, value: float) -> float:
        if value <= 0:
            raise ValueError("width and height must be positive")
        return value


class LayoutElement(BaseModel):
    id: str
    primitive_type: str
    role: str
    box: LayoutBox
    style: dict[str, Any] = Field(default_factory=dict)
    content: dict[str, Any] = Field(default_factory=dict)
    reveal_order: int | None = None


class SceneLayoutSpec(BaseModel):
    scene_id: str
    canvas: CanvasSpec = Field(default_factory=CanvasSpec)
    elements: list[LayoutElement]

    @model_validator(mode="after")
    def ensure_unique_ids(self) -> "SceneLayoutSpec":
        seen: set[str] = set()
        duplicates = []
        for element in self.elements:
            if element.id in seen:
                duplicates.append(element.id)
            seen.add(element.id)
        if duplicates:
            dupes = ", ".join(sorted(set(duplicates)))
            raise ValueError(f"duplicate element ids found: {dupes}")
        return self


class ValidationIssue(BaseModel):
    code: str
    severity: Literal["info", "warning", "error"]
    scene_id: str
    element_id: str | None = None
    target_path: str
    message: str
    repair_hint: str | None = None
    meta: dict[str, Any] = Field(default_factory=dict)


class ValidationReport(BaseModel):
    scene_id: str
    passed: bool
    issues: list[ValidationIssue] = Field(default_factory=list)


class RepairOperation(BaseModel):
    issue_code: str
    element_id: str | None = None
    action: str
    details: dict[str, Any] = Field(default_factory=dict)


class RepairResult(BaseModel):
    repaired: bool
    repaired_layout_spec: SceneLayoutSpec
    repair_operations: list[RepairOperation] = Field(default_factory=list)
    validation_report: ValidationReport
