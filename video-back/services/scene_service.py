from __future__ import annotations

from copy import deepcopy

from compiler.schemas import ScenePatch

RECOMPILE_NODE_BY_STAGE = {
    "layout": "compile_layout_node",
    "motion": "compile_motion_node",
    "dsl": "generate_dsl_node",
    "code": "generate_scene_code_node",
    "validate": "validate_scene_node",
}


def _find_scene(scenes: list[dict], scene_id: str) -> dict:
    for scene in scenes:
        if scene.get("scene_id") == scene_id:
            return scene
    raise ValueError(f"Scene not found: {scene_id}")


def prepare_scene_recompile(
    *,
    current_state: dict,
    scene_id: str,
    oral_script: str | None,
    recompile_from: str,
) -> tuple[dict, str]:
    scenes = deepcopy(current_state.get("scenes", []))
    target_scene = _find_scene(scenes, scene_id)
    if oral_script:
        target_scene["text"] = oral_script.strip()

    updated_values = {
        "oral_script": current_state.get("oral_script"),
        "scenes": scenes,
        "failed_scenes": [],
        "repairable_scenes": [],
        "regenerate_scene_id": scene_id,
        "recompile_from": recompile_from,
        "last_action": f"重编译 {scene_id} from {recompile_from}",
    }

    if recompile_from in {"layout", "motion", "dsl", "code", "validate"}:
        updated_values["layouts"] = current_state.get("layouts", {})
        updated_values["motions"] = current_state.get("motions", {})
        updated_values["dsl"] = current_state.get("dsl", {})
        updated_values["codes"] = current_state.get("codes", {})
        updated_values["validations"] = current_state.get("validations", {})

    return updated_values, RECOMPILE_NODE_BY_STAGE.get(recompile_from, "compile_layout_node")


def apply_scene_patch(*, current_state: dict, scene_id: str, patch: ScenePatch) -> tuple[dict, str]:
    target = patch.target or scene_id
    if target != scene_id:
        raise ValueError("Patch target must match scene_id")

    layouts = deepcopy(current_state.get("layouts", {}))
    scene_layout = layouts.get(scene_id)
    if scene_layout is None:
        raise ValueError("Scene layout not found")

    for op in patch.ops:
        if not op.path.startswith("/"):
            raise ValueError("Patch path must start with '/'")
        parts = [part for part in op.path.strip("/").split("/") if part]
        cursor = scene_layout
        for part in parts[:-1]:
            if part.isdigit():
                cursor = cursor[int(part)]
            else:
                cursor = cursor[part]
        key = parts[-1]
        if op.op in {"replace", "add"}:
            if key.isdigit():
                cursor[int(key)] = op.value
            else:
                cursor[key] = op.value
        elif op.op == "remove":
            if key.isdigit():
                del cursor[int(key)]
            else:
                cursor.pop(key, None)

    return (
        {
            "layouts": layouts,
            "failed_scenes": [],
            "repairable_scenes": [],
            "regenerate_scene_id": scene_id,
            "recompile_from": "motion",
            "last_action": f"应用 patch 到 {scene_id}",
        },
        "compile_motion_node",
    )
