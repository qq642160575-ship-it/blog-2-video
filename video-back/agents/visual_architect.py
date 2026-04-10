from pydantic import BaseModel, Field
from typing import List, Dict
from models.get_model import get_model
from prompts.manager import PromptManager

# 定义视觉组件协议
from pydantic import BaseModel
from typing import Dict, List, Any, Optional

example = """
1. 例: 概念转译
        - Title: 数据流可视化
        - Format type: JSON
        - Description: 包含三个核心数据模块的布局规范，展示三角形数据流关系
        - Example content: |
            {
              "theme_palette": {
                "background": "#0F0F1A",
                "primary_accent": "#00E5FF",
                "secondary_accent": "#FF4D4D",
                "text_main": "#C0C0C0",
                "error": "#FF3B30"
              },
              "layout_blueprint": [
                {
                  "id": "dataTriangle",
                  "type": "SVGGroup",
                  "visual_weight": 3,
                  "coordinates": {"x": 50, "y": 100, "width": 800, "height": 600},
                  "animation": {"type": "spring", "stiffness": 200, "dampening": 30}
                },
                {
                  "id": "codeWindow",
                  "type": "Frame",
                  "style": "border: 2px solid #00E5FF, borderRadius 12px, padding 24px",
                  "coordinates": {"x": 100, "y": 300, "width": 600, "height": 400}
                }
              ],
              "marks_definition": {
                "initTriangle": 0,
                "growNodes": 45,
                "revealCode": 90,
                "pulseError": 135
              },
              "animation_formulas": "dataTriangle采用spring缩放动画，codeWindow使用interpolate的opacity渐变，error模块触发脉冲式闪烁效果（frames 135-150）"
            }
  
     2. 例: 动态模块设计
        - Title: 交互式错误提示
        - Format type: JSON
        - Description: 包含状态切换与动画触发的完整模块定义
        - Example content: |
            {
              "theme_palette": {
                "alert": "#FF3B30",
                "text_main": "#FFFFFF",
                "highlight": "#00E5FF"
              },
              "layout_blueprint": [
                {
                  "id": "errorPopup",
                  "type": "Modal",
                  "visual_weight": 5,
                  "coordinates": {"x": 0, "y": 0, "width": 100, "height": 100},
                  "animation": {"type": "interpolate", "duration": 500}
                }
              ],
              "marks_definition": {
                "showAlert": 0,
                "expandBox": 120,
                "fadeOut": 300
              },
              "animation_formulas": "errorPopup在第0帧弹出（scale:0.3->1.0），第120帧触发expandBox动画（height:100->200），第300帧执行fadeOut操作（opacity:1->0）"
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
    position: Dict[str, Any]   # x, y, align
    size: Dict[str, Any]       # width, height
    style: Dict[str, Any]
    animation: Optional[Dict[str, Any]] = None
    svg_spec: Optional[Dict[str, Any]] = None
    content_binding: Optional[str] = None


class MarksDefinition(BaseModel):
    __root__: Dict[str, int]


class AnimationFormulas(BaseModel):
    content: str


class VisualProtocol(BaseModel):
    """
    视频视觉动效架构协议（Visual Protocol）
    用于将导演分镜 → 前端可渲染UI系统
    """

    theme_palette: ThemePalette
    layout_blueprint: List[LayoutBlueprintItem]
    marks_definition: Dict[str, int]
    animation_formulas: str


visual_architect_agent = {
    "name": "visual-architect",
    "description": "负责定义分镜的 UI 布局、交互逻辑和关键帧锚点(Marks)",
    "model": get_model('cc'),  # 逻辑严密，对结构化 JSON 的遵循度高 (gpt-4o)
    "system_prompt": PromptManager().get_system_prompt('visual_architect', example=example),
    "tools": None, # [ui_pattern_matcher, keyframe_planner] placeholders
    "response_format": VisualProtocol
}
print(visual_architect_agent.get('system_prompt'))
