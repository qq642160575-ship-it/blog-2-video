from pydantic import BaseModel, Field

from models.get_model import get_model
from prompts.manager import PromptManager
example = """
{
    "scene_id": "MatrixScene",
    "code": "function MatrixScene({ marks }) {\n  const frame = useCurrentFrame();\n  const popTime = marks.pop || 0;\n  const scale = spring({ fps: 30, frame: frame - popTime, config: { damping: 14 } });\n\n  return (\n    <AbsoluteFill style={{ backgroundColor: '#0F172A', justifyContent: 'center', alignItems: 'center' }}>\n      <div style={{ transform: `scale(${scale})`, padding: '40px', backgroundColor: '#1E293B', color: '#38BDF8', borderRadius: '16px', border: '2px solid #38BDF8', boxShadow: '0 0 20px rgba(56,189,248,0.4)', fontSize: '64px', fontWeight: 'bold' }}>\n        数据连接\n      </div>\n    </AbsoluteFill>\n  );\n}\n\nrender(<MatrixScene marks={marks} />);"
}
"""


class CoderResult(BaseModel):
    scene_id: str = Field(..., description="分镜id")
    code: str = Field(..., description="生成的代码")

coder_agent = {
    "name": "coder-agent",
    "description": "负责将视觉协议转化为 Remotion React 代码",
    "model": get_model('cc'),  # 代码生成质量，尤其是复杂动效逻辑，目前最优 (claude-3-5-sonnet)
    "system_prompt": PromptManager().get_system_prompt('coder', example=example),
    "tools": None, # [code_sandbox_validator, tailwind_linter] placeholders
    "response_format": CoderResult
}
print(coder_agent.get('system_prompt'))