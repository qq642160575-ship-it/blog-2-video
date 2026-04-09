from pydantic import BaseModel, Field
from models.get_model import get_model
from prompts.manager import PromptManager

class Result(BaseModel):
    status: str = Field(..., description="Success 或 Fail")
    suggestions: str = Field(..., description="如果为Fail，必须提供具体的修复建议，如果为Success则为空")

qa_guard_agent = {
    "name": "qa-guard",
    "description": "负责代码审计、语法校验及重试逻辑触发",
    "model": get_model('cc'),  # 质检任务需要高速度和低成本，mini 足矣 (gpt-4o-mini)
    "system_prompt": PromptManager().get_system_prompt('qa_guard', example=''),
    "tools": None, # [eslint_checker, react_node_analyzer] placeholders
    "response_format": Result
}
