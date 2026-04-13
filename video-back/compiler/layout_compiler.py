from __future__ import annotations

from compiler.schemas import LayoutNode, LayoutSpec, ScenePlan


def _slot_to_node(slot: str, scene: ScenePlan) -> LayoutNode:
    if slot == "headline":
        return LayoutNode(
            id="headline",
            kind="text",
            box={"x": 120, "y": 220, "width": 840, "height": 180},
            z_index=3,
            props={"text": scene.text},
        )
    if slot == "chatInputBox":
        return LayoutNode(
            id="chatInputBox",
            kind="panel",
            box={"x": 140, "y": 760, "width": 800, "height": 120},
            z_index=2,
            props={"label": "Prompt"},
        )
    if slot == "aiPanel":
        return LayoutNode(
            id="aiPanel",
            kind="panel",
            box={"x": 140, "y": 960, "width": 800, "height": 240},
            z_index=1,
            props={"label": "AI"},
        )
    if slot == "bulletList":
        return LayoutNode(
            id="bulletList",
            kind="text",
            box={"x": 120, "y": 760, "width": 840, "height": 360},
            z_index=1,
            props={"text": scene.text},
        )
    if slot == "callout":
        return LayoutNode(
            id="callout",
            kind="badge",
            box={"x": 140, "y": 860, "width": 720, "height": 140},
            z_index=2,
            props={"label": "关键结论"},
        )
    return LayoutNode(
        id=slot,
        kind="panel",
        box={"x": 140, "y": 860, "width": 800, "height": 220},
        z_index=1,
        props={},
    )


def compile_layouts(scenes: list[ScenePlan]) -> dict[str, LayoutSpec]:
    return {
        scene.scene_id: LayoutSpec(
            scene_id=scene.scene_id,
            nodes=[_slot_to_node(slot, scene) for slot in scene.layout_slots],
        )
        for scene in scenes
    }
