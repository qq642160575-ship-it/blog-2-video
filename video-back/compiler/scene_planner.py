from __future__ import annotations

from compiler.schemas import ParsedScript, ScenePlan

ROLE_TO_GOAL = {
    "hook": "create_curiosity",
    "problem": "frame_problem",
    "example": "show_example",
    "solution": "deliver_clarity",
    "ending": "land_takeaway",
}

ROLE_TO_SLOTS = {
    "hook": ["headline", "chatInputBox"],
    "problem": ["headline", "aiPanel"],
    "example": ["headline", "bulletList"],
    "solution": ["headline", "callout"],
    "ending": ["headline", "summaryCard"],
}

ROLE_TO_MOTION = {
    "hook": "soft_focus_in",
    "problem": "glitch_panel",
    "example": "step_reveal",
    "solution": "confidence_rise",
    "ending": "gentle_settle",
}


def build_scene_plan(parsed_script: ParsedScript) -> list[ScenePlan]:
    scenes: list[ScenePlan] = []
    for index, segment in enumerate(parsed_script.segments):
        role = segment.role or "example"
        scenes.append(
            ScenePlan(
                scene_id=f"scene_{index + 1}",
                type=role,
                text=segment.text,
                segment_id=segment.segment_id,
                narrative_role=role,
                visual_goal=ROLE_TO_GOAL.get(role, "explain_point"),
                layout_slots=ROLE_TO_SLOTS.get(role, ["headline", "contentCard"]),
                motion_profile=ROLE_TO_MOTION.get(role, "soft_focus_in"),
                priority=segment.importance,
            )
        )
    return scenes
