from pydantic import BaseModel, Field
from typing import List, Dict
from models.get_model import get_model
from prompts.manager import PromptManager

# 定义视觉组件协议
class SceneComponent(BaseModel):
    component_id: str = Field(..., description="唯一ID")
    role: str = Field(..., description="组件在画面中的角色（如：'Subject', 'Background-Decoration', 'Annotation'）")
    description: str = Field(..., description="详细的组件构造描述（如：'一个3层的垂直堆叠结构，顶层带红色闪烁，底层稳固'）")
    visual_logic: str = Field(..., description="组件的视觉逻辑（如：'使用SVG绘制不规则锯齿边缘'、'利用Tailwind渐变模拟深度感'）")
    depth_layer: int = Field(..., description="图层深度（0为背景，100为最顶层）")
    animation_mark: str = Field(..., description="对应的 Marks 触发点")

# 定义视觉架构协议
class VisualProtocol(BaseModel):
    composition_metaphor: str = Field(..., description="视觉组成的深层联系（如：'支柱与地基'、'扩散的波纹'）")
    safe_zones: List[str] = Field(..., description="标明哪些区域禁止放置元素以防遮挡（如：'Bottom-20% for Subtitles'）")
    marks: Dict[str, int] = Field(..., description="关键节奏锚点")
    components: List[SceneComponent] = Field(..., description="视觉组件列表")

example_json = {
    "composition_metaphor": "Industrial machinery and logical flow",
    "safe_zones": ["Bottom-25% for script subtitles", "Margins-5% for bleed"],
    "marks": {"engineStart": 30, "processFlow": 70, "outputComplete": 120},
    "components": [
      {
          "component_id": "core_engine",
          "role": "Subject",
          "description": "A complex 3D-effect cylinder representing the WMS Core, with rotating internal rings",
          "visual_logic": "Use SVG for concentric circles, apply CSS rotate animation with frame-based interpolation for the rings",
          "depth_layer": 50,
          "animation_mark": "engineStart"
      },
      {
          "component_id": "data_packets",
          "role": "Annotation",
          "description": "Stream of square packets flowing from top-left into the core_engine",
          "visual_logic": "Render a list of 5 squares; use interpolate to move them along a curved path using cubic-bezier logic",
          "depth_layer": 30,
          "animation_mark": "processFlow"
      }
    ]
}

visual_architect_agent = {
    "name": "visual-architect",
    "description": "负责定义分镜的 UI 布局、交互逻辑和关键帧锚点(Marks)",
    "model": get_model('cc'),  # 逻辑严密，对结构化 JSON 的遵循度高 (gpt-4o)
    "system_prompt": PromptManager().get_system_prompt('visual_architect', example=str(example_json)),
    "tools": None, # [ui_pattern_matcher, keyframe_planner] placeholders
    "response_format": VisualProtocol
}
print(visual_architect_agent.get('system_prompt'))
