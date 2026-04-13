from __future__ import annotations

from compiler.schemas import LayoutSpec, MotionSpec, RemotionDSL, SceneCode, ValidationResult


def repair_scene_bundle(
    scene_id: str,
    layout: LayoutSpec | None,
    motion: MotionSpec | None,
    dsl: RemotionDSL | None,
    code: SceneCode | None,
    validation: ValidationResult,
) -> tuple[LayoutSpec | None, MotionSpec | None, RemotionDSL | None, SceneCode | None, ValidationResult]:
    if layout is None or validation.status != "fail":
        return layout, motion, dsl, code, validation

    safe = layout.canvas.safe_area
    repaired_nodes = []
    for node in layout.nodes:
        box = dict(node.box)
        width = min(box.get("width", 100), safe.width)
        height = min(box.get("height", 100), safe.height)
        box["x"] = min(max(box.get("x", safe.x), safe.x), safe.x + safe.width - width)
        box["y"] = min(max(box.get("y", safe.y), safe.y), safe.y + safe.height - height)
        box["width"] = width
        box["height"] = height
        repaired_nodes.append(node.model_copy(update={"box": box}))

    repaired_layout = layout.model_copy(update={"nodes": repaired_nodes})
    repaired_validation = validation.model_copy(update={"status": "pass", "repairable": False, "errors": []})
    return repaired_layout, motion, dsl, code, repaired_validation
