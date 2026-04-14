from __future__ import annotations

from typing import Any

from layout.primitives import PrimitiveIntent, get_primitive_spec
from layout.schemas import CanvasSpec, LayoutBox, LayoutElement, SceneLayoutSpec
from layout.text_metrics import TextMetrics


class LayoutSolver:
    def __init__(self) -> None:
        self.text_metrics = TextMetrics()

    def solve(
        self,
        intents: list[PrimitiveIntent],
        canvas: CanvasSpec,
        scene_type: str | None = None,
    ) -> SceneLayoutSpec:
        sorted_intents = sorted(intents, key=lambda x: x.importance, reverse=True)

        template = self._select_template(scene_type or "statement")
        elements = self._apply_template(sorted_intents, canvas, template)

        return SceneLayoutSpec(
            scene_id="",
            canvas=canvas,
            elements=elements,
        )

    def _select_template(self, scene_type: str) -> str:
        template_mapping = {
            "statement": "hero_title_body",
            "contrast": "comparison_split",
            "process": "vertical_timeline",
            "timeline": "vertical_timeline",
            "data_point": "stat_panel",
            "product_demo": "screenshot_callouts",
            "quote": "quote_card",
            "emotion_peak": "hero_image",
            "chart": "chart_card",
            "code": "terminal_snippet",
            "metrics": "metric_grid",
        }
        return template_mapping.get(scene_type, "hero_title_body")

    def _apply_template(
        self,
        intents: list[PrimitiveIntent],
        canvas: CanvasSpec,
        template: str,
    ) -> list[LayoutElement]:
        if template == "hero_title_body":
            return self._layout_hero_title_body(intents, canvas)
        elif template == "comparison_split":
            return self._layout_comparison_split(intents, canvas)
        elif template == "vertical_timeline":
            return self._layout_vertical_timeline(intents, canvas)
        elif template == "stat_panel":
            return self._layout_stat_panel(intents, canvas)
        elif template == "screenshot_callouts":
            return self._layout_screenshot_callouts(intents, canvas)
        elif template == "quote_card":
            return self._layout_quote_card(intents, canvas)
        else:
            return self._layout_hero_title_body(intents, canvas)

    def _layout_hero_title_body(
        self,
        intents: list[PrimitiveIntent],
        canvas: CanvasSpec,
    ) -> list[LayoutElement]:
        elements: list[LayoutElement] = []
        safe_width = canvas.width - canvas.safe_left - canvas.safe_right
        safe_height = canvas.height - canvas.safe_top - canvas.safe_bottom

        current_y = canvas.safe_top
        reveal_order = 0

        for intent in intents:
            spec = get_primitive_spec(intent.primitive_type)
            if spec is None:
                continue

            width = min(spec.min_width, safe_width)
            height = spec.min_height

            if intent.text and spec.max_text_lines:
                estimated_lines = self.text_metrics.estimate_lines(
                    intent.text,
                    spec.min_font_size,
                    width - spec.default_padding * 2,
                )
                line_height = spec.min_font_size * 1.5
                text_height = estimated_lines * line_height + spec.default_padding * 2
                height = max(height, int(text_height))

            x = canvas.safe_left + (safe_width - width) / 2

            if current_y + height > canvas.height - canvas.safe_bottom:
                height = canvas.height - canvas.safe_bottom - current_y

            elements.append(
                LayoutElement(
                    id=intent.id,
                    primitive_type=intent.primitive_type,
                    role=intent.role,
                    box=LayoutBox(
                        x=x,
                        y=current_y,
                        width=width,
                        height=height,
                        z_index=len(elements),
                    ),
                    style={
                        "padding": spec.default_padding,
                        "fontSize": spec.min_font_size,
                    },
                    content={"text": intent.text} if intent.text else {},
                    reveal_order=reveal_order,
                )
            )

            current_y += height + 40
            reveal_order += 1

        return elements

    def _layout_comparison_split(
        self,
        intents: list[PrimitiveIntent],
        canvas: CanvasSpec,
    ) -> list[LayoutElement]:
        elements: list[LayoutElement] = []
        safe_width = canvas.width - canvas.safe_left - canvas.safe_right
        safe_height = canvas.height - canvas.safe_top - canvas.safe_bottom

        split_width = safe_width // 2 - 20

        left_intents = [i for i in intents if i.preferred_region == "left"][:2]
        right_intents = [i for i in intents if i.preferred_region == "right"][:2]

        if not left_intents and not right_intents:
            left_intents = intents[:len(intents)//2]
            right_intents = intents[len(intents)//2:]

        for idx, intent in enumerate(left_intents):
            spec = get_primitive_spec(intent.primitive_type)
            if spec is None:
                continue

            height = min(spec.min_height, safe_height // len(left_intents) - 40)
            y = canvas.safe_top + idx * (height + 40)

            elements.append(
                LayoutElement(
                    id=intent.id,
                    primitive_type=intent.primitive_type,
                    role=intent.role,
                    box=LayoutBox(
                        x=canvas.safe_left,
                        y=y,
                        width=split_width,
                        height=height,
                        z_index=len(elements),
                    ),
                    style={"padding": spec.default_padding},
                    content={"text": intent.text} if intent.text else {},
                    reveal_order=idx,
                )
            )

        for idx, intent in enumerate(right_intents):
            spec = get_primitive_spec(intent.primitive_type)
            if spec is None:
                continue

            height = min(spec.min_height, safe_height // len(right_intents) - 40)
            y = canvas.safe_top + idx * (height + 40)

            elements.append(
                LayoutElement(
                    id=intent.id,
                    primitive_type=intent.primitive_type,
                    role=intent.role,
                    box=LayoutBox(
                        x=canvas.safe_left + split_width + 40,
                        y=y,
                        width=split_width,
                        height=height,
                        z_index=len(elements),
                    ),
                    style={"padding": spec.default_padding},
                    content={"text": intent.text} if intent.text else {},
                    reveal_order=idx,
                )
            )

        return elements

    def _layout_vertical_timeline(
        self,
        intents: list[PrimitiveIntent],
        canvas: CanvasSpec,
    ) -> list[LayoutElement]:
        return self._layout_hero_title_body(intents, canvas)

    def _layout_stat_panel(
        self,
        intents: list[PrimitiveIntent],
        canvas: CanvasSpec,
    ) -> list[LayoutElement]:
        return self._layout_hero_title_body(intents, canvas)

    def _layout_screenshot_callouts(
        self,
        intents: list[PrimitiveIntent],
        canvas: CanvasSpec,
    ) -> list[LayoutElement]:
        return self._layout_hero_title_body(intents, canvas)

    def _layout_quote_card(
        self,
        intents: list[PrimitiveIntent],
        canvas: CanvasSpec,
    ) -> list[LayoutElement]:
        return self._layout_hero_title_body(intents, canvas)
