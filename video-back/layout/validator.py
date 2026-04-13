from __future__ import annotations

import math
from itertools import combinations

from layout.schemas import SceneLayoutSpec, ValidationIssue, ValidationReport
from layout.text_metrics import TextMetrics

DEFAULT_SUPPORTED_PRIMITIVES = {
    "HeroTitle",
    "BodyCard",
    "QuoteCard",
    "StatPanel",
    "MetricGrid",
    "StepTimeline",
    "ComparisonSplit",
    "ScreenshotFrame",
    "ChartCard",
    "TerminalSnippet",
    "ImageStage",
    "CalloutTag",
}


class LayoutValidator:
    def __init__(
        self,
        *,
        min_font_size: int = 28,
        max_text_lines: int = 3,
        supported_primitives: set[str] | None = None,
        text_metrics: TextMetrics | None = None,
    ) -> None:
        self.min_font_size = min_font_size
        self.max_text_lines = max_text_lines
        self.supported_primitives = supported_primitives or DEFAULT_SUPPORTED_PRIMITIVES
        self.text_metrics = text_metrics or TextMetrics()

    def validate(self, spec: SceneLayoutSpec) -> ValidationReport:
        issues: list[ValidationIssue] = []

        issues.extend(self._validate_primitives(spec))
        issues.extend(self._validate_bounds(spec))
        issues.extend(self._validate_text(spec))
        issues.extend(self._validate_collisions(spec))
        issues.extend(self._validate_layering(spec))

        return ValidationReport(
            scene_id=spec.scene_id,
            passed=not any(issue.severity == "error" for issue in issues),
            issues=issues,
        )

    def _validate_primitives(self, spec: SceneLayoutSpec) -> list[ValidationIssue]:
        issues: list[ValidationIssue] = []
        for index, element in enumerate(spec.elements):
            if element.primitive_type not in self.supported_primitives:
                issues.append(
                    ValidationIssue(
                        code="UNSUPPORTED_PRIMITIVE",
                        severity="error",
                        scene_id=spec.scene_id,
                        element_id=element.id,
                        target_path=f"elements[{index}].primitive_type",
                        message=f"Unsupported primitive: {element.primitive_type}",
                    )
                )
        return issues

    def _validate_bounds(self, spec: SceneLayoutSpec) -> list[ValidationIssue]:
        issues: list[ValidationIssue] = []
        canvas = spec.canvas
        safe_x_min = canvas.safe_x_min
        safe_y_min = canvas.safe_y_min
        safe_x_max = canvas.safe_x_max
        safe_y_max = canvas.safe_y_max

        for index, element in enumerate(spec.elements):
            bbox = self._rotated_bbox(element.box.x, element.box.y, element.box.width, element.box.height, element.box.rotation)

            if bbox["x_min"] < 0 or bbox["y_min"] < 0 or bbox["x_max"] > canvas.width or bbox["y_max"] > canvas.height:
                issues.append(
                    ValidationIssue(
                        code="BBOX_OVERFLOW",
                        severity="error",
                        scene_id=spec.scene_id,
                        element_id=element.id,
                        target_path=f"elements[{index}].box",
                        message="Element bbox exceeds the canvas bounds.",
                        repair_hint="shift_into_canvas",
                        meta=bbox,
                    )
                )

            if bbox["x_min"] < safe_x_min or bbox["y_min"] < safe_y_min or bbox["x_max"] > safe_x_max or bbox["y_max"] > safe_y_max:
                issues.append(
                    ValidationIssue(
                        code="SAFE_AREA_OVERFLOW",
                        severity="error",
                        scene_id=spec.scene_id,
                        element_id=element.id,
                        target_path=f"elements[{index}].box",
                        message="Element bbox exceeds the safe area.",
                        repair_hint="shift_into_safe_area",
                        meta=bbox,
                    )
                )

        return issues

    def _validate_text(self, spec: SceneLayoutSpec) -> list[ValidationIssue]:
        issues: list[ValidationIssue] = []
        for index, element in enumerate(spec.elements):
            text = str(element.content.get("text") or "")
            if not text:
                continue

            font_size = int(element.style.get("font_size", self.min_font_size))
            line_height = float(element.style.get("line_height", 1.2))
            padding = float(element.style.get("padding", 0))
            usable_width = max(1.0, element.box.width - padding * 2)
            usable_height = max(1.0, element.box.height - padding * 2)

            if font_size < self.min_font_size:
                issues.append(
                    ValidationIssue(
                        code="FONT_SIZE_TOO_SMALL",
                        severity="error",
                        scene_id=spec.scene_id,
                        element_id=element.id,
                        target_path=f"elements[{index}].style.font_size",
                        message=f"Font size {font_size} is below minimum {self.min_font_size}.",
                        repair_hint="increase_font_size",
                    )
                )

            lines = self.text_metrics.estimate_lines(text, font_size, usable_width)
            estimated_height = self.text_metrics.estimate_height(text, font_size, line_height, usable_width)

            if lines > self.max_text_lines or estimated_height > usable_height:
                issues.append(
                    ValidationIssue(
                        code="TEXT_OVERFLOW",
                        severity="error",
                        scene_id=spec.scene_id,
                        element_id=element.id,
                        target_path=f"elements[{index}].content.text",
                        message="Text does not fit inside the available container.",
                        repair_hint="expand_or_split_text",
                        meta={
                            "estimated_lines": lines,
                            "estimated_height": estimated_height,
                            "usable_height": usable_height,
                            "usable_width": usable_width,
                        },
                    )
                )

        return issues

    def _validate_collisions(self, spec: SceneLayoutSpec) -> list[ValidationIssue]:
        issues: list[ValidationIssue] = []
        envelopes = {
            element.id: self._rotated_bbox(element.box.x, element.box.y, element.box.width, element.box.height, element.box.rotation)
            for element in spec.elements
        }

        for left, right in combinations(spec.elements, 2):
            if self._intersects(envelopes[left.id], envelopes[right.id]):
                issues.append(
                    ValidationIssue(
                        code="ELEMENT_COLLISION",
                        severity="error",
                        scene_id=spec.scene_id,
                        element_id=right.id,
                        target_path=f"elements[{right.id}]",
                        message=f"Elements '{left.id}' and '{right.id}' overlap.",
                        repair_hint="increase_spacing",
                        meta={"other_element_id": left.id},
                    )
                )
        return issues

    def _validate_layering(self, spec: SceneLayoutSpec) -> list[ValidationIssue]:
        issues: list[ValidationIssue] = []
        ordered = [element for element in spec.elements if element.reveal_order is not None]
        ordered.sort(key=lambda item: item.reveal_order or 0)

        max_z_seen = -10_000
        for index, element in enumerate(ordered):
            if element.box.z_index < max_z_seen:
                issues.append(
                    ValidationIssue(
                        code="ZINDEX_REVEAL_MISMATCH",
                        severity="warning",
                        scene_id=spec.scene_id,
                        element_id=element.id,
                        target_path=f"elements[{index}].box.z_index",
                        message="Reveal order moves forward while z-index moves backward.",
                        repair_hint="align_z_index_to_reveal_order",
                    )
                )
            max_z_seen = max(max_z_seen, element.box.z_index)

        return issues

    def _rotated_bbox(self, x: float, y: float, width: float, height: float, rotation: float) -> dict[str, float]:
        if not rotation:
            return {
                "x_min": x,
                "y_min": y,
                "x_max": x + width,
                "y_max": y + height,
            }

        radians = math.radians(rotation)
        rotated_width = abs(width * math.cos(radians)) + abs(height * math.sin(radians))
        rotated_height = abs(width * math.sin(radians)) + abs(height * math.cos(radians))
        center_x = x + width / 2
        center_y = y + height / 2

        return {
            "x_min": center_x - rotated_width / 2,
            "y_min": center_y - rotated_height / 2,
            "x_max": center_x + rotated_width / 2,
            "y_max": center_y + rotated_height / 2,
        }

    def _intersects(self, left: dict[str, float], right: dict[str, float]) -> bool:
        return not (
            left["x_max"] <= right["x_min"]
            or right["x_max"] <= left["x_min"]
            or left["y_max"] <= right["y_min"]
            or right["y_max"] <= left["y_min"]
        )
