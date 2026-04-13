from __future__ import annotations

from compiler.schemas import LayoutSpec, MarksBundle, MotionItem, MotionSpec, ScenePlan


def _entry_for_node(kind: str, profile: str) -> str:
    if kind == "text":
        return "fadeInUp"
    if profile == "glitch_panel":
        return "glitchIn"
    if kind == "badge":
        return "popIn"
    return "scaleIn"


def compile_motions(
    scenes: list[ScenePlan],
    marks: MarksBundle,
    layouts: dict[str, LayoutSpec],
) -> dict[str, MotionSpec]:
    results: dict[str, MotionSpec] = {}
    for scene in scenes:
        layout = layouts[scene.scene_id]
        local_marks = marks.scene_marks.get(scene.scene_id, {})
        motions: list[MotionItem] = []
        for index, node in enumerate(layout.nodes):
            start = list(local_marks.values())[min(index, max(0, len(local_marks) - 1))] if local_marks else index * 10
            end = min(scene.duration_in_frames - 1, start + 12)
            motions.append(
                MotionItem(
                    target=node.id,
                    entry=_entry_for_node(node.kind, scene.motion_profile),
                    start=start,
                    end=end,
                    params={"distance": 24 if node.kind == "text" else 16},
                )
            )
        results[scene.scene_id] = MotionSpec(scene_id=scene.scene_id, motions=motions)
    return results
