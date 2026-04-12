from typing import Any, Dict, List, Optional

import json

from pydantic import BaseModel, Field, field_validator

from models.get_model import get_model

example = """
{
  "theme_palette": {
    "background": "#FDFBEE",
    "primary_accent": "#38B2AC",
    "secondary_accent": "#F6AD55",
    "text_main": "#1A1B26",
    "text_muted": "#4A5568",
    "highlight": "#FFFFFF",
    "warning": "#ECC94B",
    "error": "#F56565",
    "stroke": "#000000"
  },
  "layout_blueprint": [
    {
      "id": "mainInfoCard",
      "type": "LogicCard",
      "position": {"x": 540, "y": 900, "align": "center"},
      "size": {"width": 600, "height": 400},
      "style": {
        "backgroundColor": "#FFFFFF",
        "border": "4px solid #000000",
        "borderRadius": "24px",
        "boxShadow": "8px 8px 0px rgba(0,0,0,0.15)",
        "rotate": "-1.5deg"
      },
      "animation": {"type": "spring", "stiffness": 120, "damping": 12}
    },
    {
      "id": "painPointStamp",
      "type": "Stamp",
      "position": {"x": 800, "y": 750, "align": "right"},
      "size": {"width": 220, "height": 80},
      "style": {
        "backgroundColor": "#F6AD55",
        "border": "4px solid #000000",
        "borderRadius": "40px",
        "rotate": "8deg",
        "boxShadow": "4px 4px 0px #000000"
      },
      "animation": {"type": "spring", "stiffness": 200, "damping": 15, "delay": 0.3}
    }
  ],
  "canvas_config": {
    "background_grid": true,
    "grid_color": "#E2E8F0",
    "initial_offset": {"x": 0, "y": 0}
  },
  "marks_definition": {
    "cardDrop": 10,
    "stampSlap": 45
  },
  "animation_formulas": "mainInfoCard 以 Elastic Spring 垂坠，painPointStamp 在 1.5s 时斜着拍在卡片边缘。"
}
"""


class ThemePalette(BaseModel):
    background: str = "#FDFBEE"
    primary_accent: str = "#38B2AC"
    secondary_accent: str = "#F6AD55"
    text_main: str = "#1A1B26"
    text_muted: str = "#4A5568"
    highlight: str = "#FFFFFF"
    warning: str = "#ECC94B"
    error: str = "#F56565"
    glass_panel: Optional[str] = None
    stroke: Optional[str] = "#000000"


class LayoutBlueprintItem(BaseModel):
    id: str
    type: str
    position: Dict[str, Any]
    size: Dict[str, Any] = Field(default_factory=lambda: {"width": 720, "height": 360})
    style: Dict[str, Any] = Field(
        default_factory=lambda: {
            "backgroundColor": "#FFFFFF",
            "border": "4px solid #000000",
            "borderRadius": "24px",
            "boxShadow": "8px 8px 0px rgba(0,0,0,0.15)",
            "rotate": "-1deg",
        }
    )
    animation: Optional[Dict[str, Any]] = None
    svg_spec: Optional[Dict[str, Any]] = None
    content_binding: Optional[str] = None


class VisualProtocol(BaseModel):
    theme_palette: ThemePalette
    layout_blueprint: List[LayoutBlueprintItem]
    marks_definition: Dict[str, int]
    animation_formulas: str
    canvas_config: Optional[Dict[str, Any]] = None

    @field_validator("marks_definition", mode="before")
    @classmethod
    def flatten_marks_definition(cls, value: Any) -> Dict[str, int]:
        if not isinstance(value, dict):
            return {}

        flattened: Dict[str, int] = {}
        for key, frame in value.items():
            if isinstance(frame, dict):
                for nested_key, nested_frame in frame.items():
                    if isinstance(nested_frame, (int, float)):
                        flattened[f"{key}_{nested_key}"] = int(nested_frame)
                continue
            if isinstance(frame, (int, float)):
                flattened[str(key)] = int(frame)

        return flattened

    @field_validator("animation_formulas", mode="before")
    @classmethod
    def stringify_animation_formulas(cls, value: Any) -> str:
        if isinstance(value, str):
            return value
        return json.dumps(value, ensure_ascii=False, default=str)


visual_architect_agent = {
    "name": "visual-architect",
    "prompt_name": "visual_architect",
    "model_role": "visual_architect",
    "model": get_model("visual_architect"),
    "response_format": VisualProtocol,
}
