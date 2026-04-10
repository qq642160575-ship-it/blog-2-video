
from models.get_model import get_model
from prompts.manager import PromptManager

from pydantic import BaseModel, Field
from typing import List
example = """
1. 例1:
     - 标题: 悬念式开场构建
     - 格式类型: JSON
     - 描述: 展示如何将"这个秘密只有在深夜才会显现"转化为具象化的视觉方案
     - 内容示例:
       {
         "scene_id": "Scene 1",
         "script": "这个秘密只有在深夜才会显现",
         "visual_design": "日光灯管在凌晨3点突然亮起，照亮满墙倒挂的钟表",
         "camera_language": "从俯视角度慢推，镜头在日光灯管上做0.8秒的微距变焦",
         "visual_elements": "12个倒挂钟表/日光灯管/尘埃漂浮/机械齿轮特写",
         "visual_transition": "灯光渐变+齿轮转动的机械音效",
         "emotion_rhythm": "悬念（强度3.2）→好奇（强度2.8）→紧张（强度4.1）"
       }
  
  2. 例2:
     - 标题: 科普类内容可视化转化
     - 格式类型: JSON
     - 描述: 显示如何将"量子纠缠现象"转化为可视觉化的分镜方案
     - 内容示例:
       {
         "scene_id": "Scene 5",
         "script": "量子纠缠现象是两个粒子在产生后，即使相隔千里也能瞬间影响彼此",
         "visual_design": "分离的棋子在不同棋盘上产生波动，同时呈现波纹传导效果",
         "camera_language": "使用环绕镜头展示粒子运动轨迹，0.5秒切镜突出波动瞬间",
         "visual_elements": "荧光棋子/量子波纹动画/粒子运动轨迹/实验室场景",
         "visual_transition": "粒子分离动画→波纹扩散→同步闪烁",
         "emotion_rhythm": "解释（强度2.5）→惊讶（强度4.0）→理解（强度3.0）"
       }

"""

class Scene(BaseModel):
    # 🎥 Scene 编号
    scene_id: str = Field(..., description="分镜编号，例如 Scene 1 / Scene 2，用于唯一标识当前镜头")
    # 🧾 原文口播（必须100%原封不动）
    script: str = Field(..., description="必须原封不动引用的口播原文，不得改写、不得总结、不得删减")
    # 🎬 画面设计（导演级具象化描述）
    visual_design: str = Field(..., description="从导演视角描述画面内容，必须具象化（空间、物体、动作），禁止抽象总结")
    # 📷 镜头语言（运镜设计）
    camera_language: str = Field(..., description="镜头运动方式，如推镜、拉镜、俯冲、跟拍、切镜、环绕镜头等")
    # 🧩 视觉元素（构成系统）
    visual_elements: str = Field(..., description="画面中的具体视觉构成，包括人物、UI界面、空间结构、隐喻物体、动态系统")
    # 🎞️ 视觉变化（时间维度变化）
    visual_transition: str = Field(..., description="画面随时间变化的过程，包括动画、崩塌、压缩、流动、扩展、转场等")
    # ⚡ 情绪节奏（观众心理曲线）
    emotion_rhythm: str = Field(..., description="当前镜头的情绪状态，如悬念、解释、冲击、轻松、强化、反转等")
    # 技术实现方案
    code_render_model: str = Field(..., description="技术实现方案（代码级）")
    # 关键帧标记
    animation_marks: dict = Field(..., description="时间轴动画锚点系统（关键帧标记）")

class Validation(BaseModel):
    semantic_coverage: str = Field(..., description="语义覆盖度")
    visual_feasibility: str = Field(..., description="视觉可实现性")
    platform_adaptability: str = Field(..., description="平台适配度")
    narrative_continuity: str = Field(..., description="叙事连续性")
    emotion_curve_compliance: str = Field(..., description="情绪曲线符合度")

class DirectorResult(BaseModel):
    # 🎬 完整分镜列表（按叙事顺序）
    scenes: List[Scene] = Field(
        ...,
        description="完整短视频分镜列表，必须严格按照叙事顺序排列，不得跳跃或重组"
    )
    validation: Validation = Field(..., description="是否“可用 + 可拍 + 可传播”的质量检测报告")

director_agent = {
    "name": "director-agent",
    "description": "负责将“口播文稿”转化为高质量视觉分镜",
    "model": get_model('cc'),  # 语义理解与文学创作能力极强 (claude-3-5-sonnet)
    "system_prompt": PromptManager().get_system_prompt('director', example=example),
    "tools": None, # [text_segmenter, timing_calculator] placeholders
    "response_format": DirectorResult
}
print(director_agent.get('system_prompt'))