from pydantic import BaseModel, Field

from models.get_model import get_model

example = """
{
  "scene_id": "MatrixScene",
  "code": "function MatrixScene({ marks }) { return null; } render(<MatrixScene marks={marks} />);"
}
"""


class CoderResult(BaseModel):
    scene_id: str = Field(..., description="分镜 id，必须和输入 scene_id 保持一致")
    code: str = Field(..., description="生成的 Remotion React 代码")


coder_agent = {
    "name": "coder-agent",
    "prompt_name": "coder",
    "model_role": "coder",
    "model": get_model("coder"),
    "response_format": CoderResult,
}
