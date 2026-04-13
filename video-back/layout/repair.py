from __future__ import annotations

from copy import deepcopy

from layout.schemas import RepairOperation, RepairResult, SceneLayoutSpec
from layout.validator import LayoutValidator


class RepairService:
    def __init__(self, validator: LayoutValidator | None = None) -> None:
        self.validator = validator or LayoutValidator()

    def repair(self, spec: SceneLayoutSpec) -> RepairResult:
        working = deepcopy(spec)
        initial_report = self.validator.validate(working)
        operations: list[RepairOperation] = []

        for issue in initial_report.issues:
            if issue.element_id is None:
                continue

            element = next((item for item in working.elements if item.id == issue.element_id), None)
            if element is None:
                continue

            if issue.code in {"SAFE_AREA_OVERFLOW", "BBOX_OVERFLOW"}:
                self._shift_into_safe_area(working, element)
                operations.append(
                    RepairOperation(
                        issue_code=issue.code,
                        element_id=element.id,
                        action="shift_into_safe_area",
                    )
                )
            elif issue.code == "TEXT_OVERFLOW":
                action = self._repair_text_overflow(working, element)
                operations.append(
                    RepairOperation(
                        issue_code=issue.code,
                        element_id=element.id,
                        action=action,
                    )
                )
            elif issue.code == "FONT_SIZE_TOO_SMALL":
                element.style["font_size"] = self.validator.min_font_size
                operations.append(
                    RepairOperation(
                        issue_code=issue.code,
                        element_id=element.id,
                        action="increase_font_size",
                        details={"font_size": self.validator.min_font_size},
                    )
                )
            elif issue.code == "ELEMENT_COLLISION":
                other_id = issue.meta.get("other_element_id")
                other = next((item for item in working.elements if item.id == other_id), None)
                if other is not None:
                    element.box.y = max(element.box.y, other.box.y + other.box.height + 24.0)
                else:
                    offset = max(24.0, element.box.height * 0.2)
                    element.box.y += offset
                operations.append(
                    RepairOperation(
                        issue_code=issue.code,
                        element_id=element.id,
                        action="shift_down",
                        details={"other_element_id": other_id},
                    )
                )
            elif issue.code == "ZINDEX_REVEAL_MISMATCH":
                element.box.z_index = max(element.box.z_index, element.reveal_order or element.box.z_index)
                operations.append(
                    RepairOperation(
                        issue_code=issue.code,
                        element_id=element.id,
                        action="align_z_index_to_reveal_order",
                        details={"z_index": element.box.z_index},
                    )
                )

        final_report = self.validator.validate(working)
        return RepairResult(
            repaired=bool(operations),
            repaired_layout_spec=working,
            repair_operations=operations,
            validation_report=final_report,
        )

    def _shift_into_safe_area(self, spec: SceneLayoutSpec, element) -> None:
        canvas = spec.canvas
        x_min = canvas.safe_x_min
        y_min = canvas.safe_y_min
        x_max = canvas.safe_x_max
        y_max = canvas.safe_y_max

        if element.box.x < x_min:
            element.box.x = x_min
        if element.box.y < y_min:
            element.box.y = y_min
        if element.box.x + element.box.width > x_max:
            element.box.x = max(x_min, x_max - element.box.width)
        if element.box.y + element.box.height > y_max:
            element.box.y = max(y_min, y_max - element.box.height)
        if element.box.rotation:
            element.box.rotation = 0.0

    def _repair_text_overflow(self, spec: SceneLayoutSpec, element) -> str:
        padding = float(element.style.get("padding", 0))
        text = str(element.content.get("text") or "")
        font_size = int(element.style.get("font_size", self.validator.min_font_size))
        line_height = float(element.style.get("line_height", 1.2))
        usable_width = max(1.0, element.box.width - padding * 2)
        estimated_height = self.validator.text_metrics.estimate_height(text, font_size, line_height, usable_width)
        required_height = estimated_height + padding * 2

        if required_height > element.box.height:
            max_safe_height = spec.canvas.safe_y_max - element.box.y
            grown_height = min(max_safe_height, required_height)
            if grown_height > element.box.height:
                element.box.height = grown_height
                return "expand_container"

        if font_size > self.validator.min_font_size:
            element.style["font_size"] = max(self.validator.min_font_size, font_size - 4)
            return "reduce_font_size"

        paragraphs = [part.strip() for part in text.replace("\r\n", "\n").split("\n") if part.strip()]
        if len(paragraphs) > 1:
            element.content["text"] = "\n".join(paragraphs[: self.validator.max_text_lines])
            return "trim_to_multiline"

        return "expand_container"
