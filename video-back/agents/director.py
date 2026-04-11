from typing import List

from pydantic import BaseModel, Field, field_validator

from models.get_model import get_model

example = """
## 完整输出结构示例:
{
  "scenes": [
    {
      "scene_id": "Scene 1",
      "script": "这个秘密只有在深夜才会显现",
      "visual_design": "日光灯管在凌晨 3 点突然亮起，照亮满墙倒挂的钟表",
      "camera_language": "从俯视角度慢推，镜头在日光灯管上停 0.8 秒后微距变焦",
      "visual_elements": "12 个倒挂钟表/日光灯管/尘埃漂浮/机械齿轮特写",
      "visual_transition": "灯光渐变 + 齿轮转动的机械音效",
      "emotion_rhythm": "悬念（强度 0.2）→好奇（强度 0.8）→紧张（强度 1.1）",
      "code_render_model": "基于 Remotion 的纯 React 组件，使用 SVG 绘制钟表并使用 spring() 实现倒挂坠落动画",
      "animation_marks": {
        "light_on": 10,
        "zoom_start": 30,
        "gear_turn": 60
      }
    }
  ],
  "validation": {
    "semantic_coverage": "完美匹配原文概念，无语义遗漏",
    "visual_feasibility": "纯代码实现度高，依赖基础图形和位移动画",
    "platform_adaptability": "符合短视频快节奏切镜风格",
    "narrative_continuity": "从宏观氛围直接切入微观粒子，通过光影变化保持连贯",
    "emotion_curve_compliance": "开场悬念迅速转入硬核科普，情绪抓力强"
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
    animation_marks: dict = Field(..., description="时间轴动画锚点系统")


class Validation(BaseModel):
    semantic_coverage: str = Field(..., description="语义覆盖度")
    visual_feasibility: str = Field(..., description="视觉可实现性")
    platform_adaptability: str = Field(..., description="平台适配度")
    narrative_continuity: str = Field(..., description="叙事连续性")
    emotion_curve_compliance: str = Field(..., description="情绪曲线符合度")


class DirectorResult(BaseModel):
    scenes: List[Scene] = Field(..., description="完整短视频分镜列表，必须严格按照叙事顺序排列")
    validation: Validation = Field(..., description="可用性与传播性验证结果")

    @field_validator("scenes", mode="before")
    @classmethod
    def parse_scenes(cls, value):
        import json

        if isinstance(value, str):
            try:
                value = json.loads(value)
            except Exception:
                pass
        return value


director_agent = {
    "name": "director-agent",
    "prompt_name": "director",
    "model_role": "director",
    "model": get_model("director"),
    "response_format": DirectorResult,
}
