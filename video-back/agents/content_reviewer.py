from pydantic import BaseModel, Field

from models.get_model import get_model


class Result(BaseModel):
    score: int = Field(..., description="0-100 分的审稿得分")
    feedback: str = Field(..., description="评审反馈，低于阈值时给出具体修改建议")


content_reviewer_agent = {
    "name": "content-reviewer",
    "prompt_name": "content_reviewer",
    "model_role": "reviewer",
    "model": get_model("reviewer"),
    "response_format": Result,
}
