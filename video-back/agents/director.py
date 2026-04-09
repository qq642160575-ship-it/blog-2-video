from pydantic import BaseModel, Field

from models.get_model import get_model
from prompts.manager import PromptManager
example = """
    示例输入：
    内容：“并发关注的是任务的调度，而不是执行方式。”

    示例输出：
    {
      "scene_id": 1,
      "script": "很多人以为并发就是多线程，但这其实是一个巨大的误区。",
      "emotion": "震惊",
      "visual_metaphor": "一个正在崩塌的‘多线程’积木塔",
      "spatial_focus": "中心汇聚，视觉压力集中在底部",
      "pacing": "突然的镜头拉近，伴随积木倒塌的节奏感"
    }
"""

class Result(BaseModel):
    scene_id: int = Field(..., description="场景ID")
    script: str = Field(..., description="场景口语化文案")
    emotion: str = Field(..., description="情感基调（如：震惊、好奇、权威）")
    visual_metaphor: str = Field(..., description="本屏的核心视觉隐喻（如：'一架失衡的天平'、'正在消失的进度条'）")
    spatial_focus: str = Field(..., description="画面重心布局（如：'左重右轻'、'中心汇聚'、'顶部悬浮'）")
    pacing: str = Field(..., description="运动节奏（如：突然加速、缓慢平滑、节奏感抖动）")

director_agent = {
    "name": "director-agent",
    "description": "负责博文的语义拆解、口语化重写及视觉分镜规划",
    "model": get_model('cc'),  # 语义理解与文学创作能力极强 (claude-3-5-sonnet)
    "system_prompt": PromptManager().get_system_prompt('director', example=example),
    "tools": None, # [text_segmenter, timing_calculator] placeholders
    "response_format": Result
}
print(director_agent.get('system_prompt'))