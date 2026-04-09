from pydantic import BaseModel, Field
from models.get_model import get_model
from prompts.manager import PromptManager

class Result(BaseModel):
    oral_script: str = Field(..., description="转化后的完整生动口语化长文案内容")

content_writer_agent = {
    "name": "content-writer",
    "description": "内容预处理专家：负责将枯燥的原始技术博文转化为适合短视频播放的生动口语化文案",
    "model": get_model('cc'),  # 强在语义理解和文学创作
    "system_prompt": PromptManager().get_system_prompt('content_writer', example=""),
    "tools": None,
    "response_format": Result
}
