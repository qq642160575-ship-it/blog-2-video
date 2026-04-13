from __future__ import annotations

from compiler.schemas import MarksBundle, ScenePlan


def _scene_duration_in_frames(text: str, fps: int) -> int:
    text_len = max(1, len(text.strip()))
    estimated_seconds = max(1.5, min(6.0, text_len / 10))
    frames = int(round(estimated_seconds * fps))
    return max(fps, frames)


def build_marks(scenes: list[ScenePlan], fps: int = 30) -> tuple[list[ScenePlan], MarksBundle]:
    current_frame = 0
    updated_scenes: list[ScenePlan] = []
    global_marks: dict[str, int] = {}
    scene_marks: dict[str, dict[str, int]] = {}

    for scene in scenes:
        duration = _scene_duration_in_frames(scene.text, fps)
        start = current_frame
        end = start + duration
        updated_scene = scene.model_copy(
            update={
                "start": start,
                "end": end,
                "duration_in_frames": duration,
            }
        )
        updated_scenes.append(updated_scene)
        global_marks[scene.scene_id] = start
        scene_marks[scene.scene_id] = {
            "headlineIn": 0,
            "contentIn": min(duration - 1, max(8, fps // 2)),
            "accentIn": min(duration - 1, max(16, fps)),
        }
        current_frame = end

    return updated_scenes, MarksBundle(
        fps=fps,
        duration_in_frames=current_frame,
        global_marks=global_marks,
        scene_marks=scene_marks,
    )
