from typing import Any, Dict

LAYOUT_SLOT_PRESETS: Dict[str, Dict[str, int]] = {
    "headline": {"x": 120, "y": 220, "width": 840, "height": 180},
    "chatInputBox": {"x": 140, "y": 760, "width": 800, "height": 120},
    "aiPanel": {"x": 140, "y": 920, "width": 800, "height": 420},
    "default_text": {"x": 140, "y": 500, "width": 800, "height": 200},
}

SCENE_TYPE_MAPPING = {
    "hook": ["headline", "chatInputBox"],
    "problem_explanation": ["headline", "default_text", "aiPanel"],
    "solution": ["headline", "default_text"],
    "call_to_action": ["headline"]
}

DEFAULT_MOTION_PROFILES = {
    "hook": "soft_focus_in",
    "problem_explanation": "fade_in_up",
    "solution": "panel_scale_in",
    "call_to_action": "pulse"
}
