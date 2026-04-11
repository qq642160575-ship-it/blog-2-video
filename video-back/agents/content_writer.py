from pydantic import BaseModel, Field

from models.get_model import get_model


class Result(BaseModel):
    oral_script: str = Field(..., description="转化后的完整口语化长文案内容")


content_writer_agent = {
    "name": "content-writer",
    "prompt_name": "content_writer",
    "model_role": "writer",
    "model": get_model("writer"),
    "response_format": Result,
}
