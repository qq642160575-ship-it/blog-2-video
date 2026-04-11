from typing import Any, Dict, List, Optional

from pydantic import BaseModel

from models.get_model import get_model

example = """
{
  "theme_palette": {
    "background": "#0F0F1A",
    "primary_accent": "#00E5FF",
    "secondary_accent": "#FF4D4D",
    "text_main": "#C0C0C0",
    "text_muted": "#94A3B8",
    "highlight": "#F8FAFC",
    "warning": "#F59E0B",
    "error": "#FF3B30"
  },
  "layout_blueprint": [
    {
      "id": "dataTriangle",
      "type": "SVGGroup",
      "position": {"x": 50, "y": 100, "align": "center"},
      "size": {"width": 800, "height": 600},
      "style": {"opacity": 1},
      "animation": {"type": "spring", "stiffness": 200, "damping": 30}
    }
  ],
  "marks_definition": {
    "initTriangle": 0,
    "growNodes": 45,
    "revealCode": 90
  },
  "animation_formulas": "dataTriangle 使用 spring 缩放，codeWindow 使用 opacity 渐变。"
}
"""


class ThemePalette(BaseModel):
    background: str
    primary_accent: str
    secondary_accent: str
    text_main: str
    text_muted: str
    highlight: str
    warning: str
    error: str
    glass_panel: Optional[str] = None
    stroke: Optional[str] = None


class LayoutBlueprintItem(BaseModel):
    id: str
    type: str
    position: Dict[str, Any]
    size: Dict[str, Any]
    style: Dict[str, Any]
    animation: Optional[Dict[str, Any]] = None
    svg_spec: Optional[Dict[str, Any]] = None
    content_binding: Optional[str] = None


class VisualProtocol(BaseModel):
    theme_palette: ThemePalette
    layout_blueprint: List[LayoutBlueprintItem]
    marks_definition: Dict[str, int]
    animation_formulas: str


visual_architect_agent = {
    "name": "visual-architect",
    "prompt_name": "visual_architect",
    "model_role": "visual_architect",
    "model": get_model("visual_architect"),
    "response_format": VisualProtocol,
}
