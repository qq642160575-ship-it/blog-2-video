from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class RenderRequest(BaseModel):
    """渲染请求"""

    scene_id: str
    scene_code: str
    frame: int = 0
    width: int = 1080
    height: int = 1920
    metadata: dict[str, Any] = {}


class RenderResult(BaseModel):
    """渲染结果"""

    scene_id: str
    storage_url: str
    width: int
    height: int
    frame: int
    metadata: dict[str, Any] = {}
    render_time_ms: float = 0.0


class ValidationIssue(BaseModel):
    """视觉验证问题"""

    code: str
    severity: str  # "info", "warning", "error"
    message: str
    detail: dict[str, Any] = {}


class VisualValidationReport(BaseModel):
    """视觉验证报告"""

    scene_id: str
    passed: bool
    issues: list[ValidationIssue] = []
    metadata: dict[str, Any] = {}
