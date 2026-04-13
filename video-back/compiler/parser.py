from __future__ import annotations

import re
import uuid

from compiler.schemas import ParsedScript, ScriptSegment

ROLE_ORDER = ("hook", "problem", "example", "solution", "ending")


def _split_sentences(text: str) -> list[str]:
    normalized = re.sub(r"\s+", " ", text.strip())
    if not normalized:
        return []
    pieces = re.split(r"(?<=[。！？!?；;])\s*", normalized)
    return [piece.strip() for piece in pieces if piece.strip()]


def _role_for_index(index: int, total: int) -> str:
    if total <= 1:
        return "hook"
    if index == 0:
        return "hook"
    if index == total - 1:
        return "ending"
    if index == 1:
        return "problem"
    if index == total - 2:
        return "solution"
    return "example"


def parse_script(source_text: str) -> ParsedScript:
    sentences = _split_sentences(source_text)
    if not sentences:
        raise ValueError("Source text is empty")

    segments = [
        ScriptSegment(
            segment_id=f"seg_{index + 1}",
            text=sentence,
            role=_role_for_index(index, len(sentences)),
            importance=max(1, min(5, 5 - index if index < 3 else 3)),
        )
        for index, sentence in enumerate(sentences)
    ]

    return ParsedScript(
        source_id=str(uuid.uuid4()),
        intent="problem_explanation" if len(sentences) > 1 else "single_point",
        tone="conversational",
        emotion_curve=[segment.role for segment in segments[:4]],
        segments=segments,
    )
