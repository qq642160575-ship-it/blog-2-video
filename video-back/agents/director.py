from typing import List

from pydantic import BaseModel, Field, field_validator

from models.get_model import get_model

example = """
## 完整输出结构示例:
{
  "art_direction": "Vizplainer 画布风 (Canvas Architecture)",
  "scenes": [
    {
      "scene_id": "Scene 1",
      "script": "做 AI Agent 最痛苦的事，就是明明看了很多教程，最后还是做不对。",
      "visual_design": "暖米色网格画布中心，一个 LogicCard 贴纸弹跳进场，上方斜贴一个黄色 Stamp 标注'PAIN POINT'。右侧预留出 FlowNode 准备空间。",
      "camera_language": "固定视角，准备向右平移",
      "visual_elements": "LogicCard(中心)/Stamp(右偏转)/米色坐标纸底纹",
      "visual_transition": "LogicCard 以弹簧效果(Spring)垂直落下，Stamp 随后以 12 度倾向'拍'在它右角。",
      "emotion_rhythm": "沮丧（强度 0.8）",
      "code_render_model": "AbsoluteFill + GridPattern。LogicCard 使用 border: 4px solid #000 且带 rotate: -2deg。Stamp 使用 scale 动画进场。",
      "duration": 4.5,
      "animation_marks": {
        "cardDrop": 10,
        "stampSlap": 45
      }
    }
  ],
  "validation": {
    "semantic_coverage": "完美复现了对于'痛苦'的物理具象化表达",
    "visual_feasibility": "贴纸与物理弹簧动效是 Vizplainer 风格的核心，纯代码实现极稳",
    "platform_adaptability": "画布风格具有极强的视觉连续性，适合长频讲解",
    "narrative_continuity": "为下一镜头的画布平移做好了空间布局预留",
    "emotion_curve_compliance": "低沉的文案配合厚重的贴纸拍击感，情绪共鸣强"
  }
}
"""


class Scene(BaseModel):
    scene_id: str = Field(..., description="分镜编号，例如 Scene 1 / Scene 2，用于唯一标识当前镜头")
    script: str = Field(..., description="必须原封不动引用的口播原文，不得改写、总结或删减")
    visual_design: str = Field(..., description="从导演视角描述画面内容，必须具体化")
    camera_language: str = Field(..., description="镜头运动方式")
    visual_elements: str = Field(..., description="画面中的具体视觉构成")
    visual_transition: str = Field(..., description="画面随时间变化的过程")
    emotion_rhythm: str = Field(..., description="当前镜头的情绪节奏")
    code_render_model: str = Field(..., description="技术实现方案")
    duration: float = Field(..., description="预计时长（秒），根据文案字数估算（每秒约4-5个字）")
    animation_marks: dict = Field(..., description="时间轴动画锚点系统")


class Validation(BaseModel):
    semantic_coverage: str = Field(..., description="语义覆盖度")
    visual_feasibility: str = Field(..., description="视觉可实现性")
    platform_adaptability: str = Field(..., description="平台适配度")
    narrative_continuity: str = Field(..., description="叙事连续性")
    emotion_curve_compliance: str = Field(..., description="情绪曲线符合度")


class DirectorResult(BaseModel):
    art_direction: str = Field(..., description="全局视觉美术指导风格，例如 'Vizplainer 画布风'，根据文案内容动态决定风格")
    scenes: List[Scene] = Field(..., description="完整短视频分镜列表，必须严格按照叙事顺序排列")
    validation: Validation = Field(..., description="可用性与传播性验证结果")


director_agent = {
    "name": "director-agent",
    "prompt_name": "director",
    "model_role": "director",
    "model": get_model("director"),
    "response_format": DirectorResult,
}
