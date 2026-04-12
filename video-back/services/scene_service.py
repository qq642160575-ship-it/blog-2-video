import json
from typing import Any

from utils.logger import get_logger
from utils.cache import build_cache_key
from workflow.animation_work_flow import coder_cache

logger = get_logger(__name__)


def _scene_id(scene: Any) -> str | None:
    if isinstance(scene, dict):
        return scene.get("scene_id")
    return getattr(scene, "scene_id", None)


def _update_scene_fields(scene: Any, script: str, visual_design: str) -> Any:
    if isinstance(scene, dict):
        updated = dict(scene)
        updated["script"] = script
        updated["visual_design"] = visual_design
        return updated

    scene.script = script
    scene.visual_design = visual_design
    return scene


def _dump_json(value: Any) -> str:
    if hasattr(value, "model_dump_json"):
        return value.model_dump_json()
    return json.dumps(value, ensure_ascii=False, default=str)


def update_director_scenes(director_result: Any, scene_id: str, script: str, visual_design: str) -> tuple[Any, Any]:
    updated_scenes = []
    target_scene = None

    scenes = director_result.get("scenes", []) if isinstance(director_result, dict) else director_result.scenes
    for scene in scenes:
        if _scene_id(scene) == scene_id:
            scene = _update_scene_fields(scene, script, visual_design)
            target_scene = scene
        updated_scenes.append(scene)

    if target_scene is None:
        raise ValueError(f"Scene not found: {scene_id}")

    if isinstance(director_result, dict):
        updated_director_result = dict(director_result)
        updated_director_result["scenes"] = updated_scenes
    else:
        director_result.scenes = updated_scenes
        updated_director_result = director_result

    logger.info("Scene updated scene_id=%s", scene_id)
    return updated_director_result, target_scene


def clear_scene_coder_cache(scene: Any, visual_architect: Any) -> bool:
    if not visual_architect:
        logger.debug("Skip coder cache clear because visual_architect is missing")
        return False

    cache_key = build_cache_key("coder-agent", _dump_json(scene), _dump_json(visual_architect))
    deleted = coder_cache.delete(cache_key)
    logger.info("Scene coder cache clear scene_id=%s deleted=%s", _scene_id(scene), deleted)
    return deleted
