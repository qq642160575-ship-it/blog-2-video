from __future__ import annotations

from compiler.schemas import LayoutSpec, MotionSpec, RemotionDSL, SceneCode, ValidationErrorItem, ValidationResult


def validate_scene_bundle(
    scene_id: str,
    layout: LayoutSpec | None,
    motion: MotionSpec | None,
    dsl: RemotionDSL | None,
    code: SceneCode | None,
) -> ValidationResult:
    errors: list[ValidationErrorItem] = []

    if layout is None:
        errors.append(ValidationErrorItem(code="LAYOUT_NODE_MISSING", scene_id=scene_id, stage="layout"))
    else:
        safe = layout.canvas.safe_area
        for node in layout.nodes:
            x = node.box.get("x", 0)
            y = node.box.get("y", 0)
            width = node.box.get("width", 0)
            height = node.box.get("height", 0)
            if x < safe.x or y < safe.y or x + width > safe.x + safe.width or y + height > safe.y + safe.height:
                errors.append(
                    ValidationErrorItem(
                        code="LAYOUT_OVERFLOW",
                        scene_id=scene_id,
                        node_id=node.id,
                        stage="layout",
                        message="Node is outside the mobile safe area",
                    )
                )

    if motion and layout:
        layout_ids = {node.id for node in layout.nodes}
        for item in motion.motions:
            if item.target not in layout_ids:
                errors.append(
                    ValidationErrorItem(
                        code="MOTION_TARGET_NOT_FOUND",
                        scene_id=scene_id,
                        node_id=item.target,
                        stage="motion",
                    )
                )

    if dsl is None:
        errors.append(ValidationErrorItem(code="DSL_INVALID_COMPONENT", scene_id=scene_id, stage="dsl"))
    if code is None:
        errors.append(ValidationErrorItem(code="CODE_RENDER_MISSING", scene_id=scene_id, stage="code"))
    elif "render(" not in code.code:
        errors.append(ValidationErrorItem(code="CODE_RENDER_MISSING", scene_id=scene_id, stage="code"))

    status = "pass" if not errors else "fail"
    return ValidationResult(
        scene_id=scene_id,
        status=status,
        stage=errors[0].stage if errors else "validation",
        repairable=any(error.code == "LAYOUT_OVERFLOW" for error in errors),
        errors=errors,
    )
