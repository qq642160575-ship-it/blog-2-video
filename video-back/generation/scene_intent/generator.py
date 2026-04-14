from __future__ import annotations

from typing import Any

from layout.primitives import PrimitiveIntent
from layout.primitives import get_primitives_for_scene_type


class SceneIntentGenerator:
    def generate(
        self,
        scene: dict[str, Any],
        visual_strategy: dict[str, Any],
    ) -> list[PrimitiveIntent]:
        scene_type = scene.get("scene_type", "statement")
        script_text = scene.get("script", "")
        scene_id = scene.get("scene_id", "")

        allowed_primitives = get_primitives_for_scene_type(scene_type)

        intents: list[PrimitiveIntent] = []

        if scene_type == "statement":
            intents.append(
                PrimitiveIntent(
                    id=f"{scene_id}_title",
                    role="title",
                    primitive_type="HeroTitle",
                    importance=100,
                    text=self._extract_title(script_text),
                    preferred_region="top",
                )
            )
            body_text = self._extract_body(script_text)
            if body_text:
                intents.append(
                    PrimitiveIntent(
                        id=f"{scene_id}_body",
                        role="body",
                        primitive_type="BodyCard",
                        importance=80,
                        text=body_text,
                        preferred_region="middle",
                    )
                )

        elif scene_type == "data_point":
            intents.append(
                PrimitiveIntent(
                    id=f"{scene_id}_stat",
                    role="stat",
                    primitive_type="StatPanel",
                    importance=100,
                    text=self._extract_stat(script_text),
                    preferred_region="top",
                )
            )
            explanation = self._extract_explanation(script_text)
            if explanation:
                intents.append(
                    PrimitiveIntent(
                        id=f"{scene_id}_explanation",
                        role="body",
                        primitive_type="BodyCard",
                        importance=70,
                        text=explanation,
                        preferred_region="bottom",
                    )
                )

        elif scene_type == "quote":
            intents.append(
                PrimitiveIntent(
                    id=f"{scene_id}_quote",
                    role="quote",
                    primitive_type="QuoteCard",
                    importance=100,
                    text=script_text,
                    preferred_region="middle",
                )
            )

        elif scene_type == "contrast":
            parts = self._split_contrast(script_text)
            intents.append(
                PrimitiveIntent(
                    id=f"{scene_id}_left",
                    role="comparison_left",
                    primitive_type="BodyCard",
                    importance=100,
                    text=parts[0],
                    preferred_region="left",
                )
            )
            if len(parts) > 1:
                intents.append(
                    PrimitiveIntent(
                        id=f"{scene_id}_right",
                        role="comparison_right",
                        primitive_type="BodyCard",
                        importance=100,
                        text=parts[1],
                        preferred_region="right",
                    )
                )

        else:
            intents.append(
                PrimitiveIntent(
                    id=f"{scene_id}_title",
                    role="title",
                    primitive_type="HeroTitle",
                    importance=100,
                    text=self._extract_title(script_text),
                )
            )

        return intents

    def _extract_title(self, text: str) -> str:
        lines = text.strip().split("\n")
        return lines[0] if lines else text[:50]

    def _extract_body(self, text: str) -> str:
        lines = text.strip().split("\n")
        return "\n".join(lines[1:]) if len(lines) > 1 else ""

    def _extract_stat(self, text: str) -> str:
        import re
        match = re.search(r"\d+[%\w]*", text)
        return match.group(0) if match else text[:20]

    def _extract_explanation(self, text: str) -> str:
        import re
        text_without_stat = re.sub(r"\d+[%\w]*", "", text)
        return text_without_stat.strip()

    def _split_contrast(self, text: str) -> list[str]:
        separators = ["vs", "versus", "对比", "相比", "而"]
        for sep in separators:
            if sep in text.lower():
                parts = text.split(sep, 1)
                return [p.strip() for p in parts]
        mid = len(text) // 2
        return [text[:mid].strip(), text[mid:].strip()]
