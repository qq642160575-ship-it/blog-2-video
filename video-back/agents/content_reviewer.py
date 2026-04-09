from pydantic import BaseModel, Field
from models.get_model import get_model
from prompts.manager import PromptManager

class Result(BaseModel):
    score: int = Field(..., description="0-100分的评审得分")
    feedback: str = Field(..., description="打分低于80分时，给出的具体修改建议；高于等于80分则写'合格'")

content_reviewer_agent = {
    "name": "content-reviewer",
    "description": "文案评审总监：对比原始博文和口语化文案，打分并提供重写建议（分数>=80为合格）",
    "model": get_model('cc'),  # 最好是 gpt-4o, 逻辑严苛负责打分
    "system_prompt": PromptManager().get_system_prompt('content_reviewer', example=""),
    "tools": None,
    "response_format": Result
}
