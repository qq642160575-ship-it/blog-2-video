from pydantic import BaseModel, Field

from models.get_model import get_model


class Result(BaseModel):
    status: str = Field(..., description="Success 或 Fail")
    suggestions: str = Field(..., description="当状态为 Fail 时给出具体修复建议")


qa_guard_agent = {
    "name": "qa-guard",
    "prompt_name": "qa_guard",
    "model_role": "qa",
    "model": get_model("qa"),
    "response_format": Result,
}
