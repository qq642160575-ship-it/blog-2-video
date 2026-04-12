from pydantic import BaseModel, Field

from models.get_model import get_model

example = """
{
  "scene_id": "CanvasScene",
  "code": "function CanvasScene({ marks }) { const frame = useCurrentFrame(); const { fps } = useVideoConfig(); const cardSpring = spring({ frame, fps, delay: marks.cardDrop || 0, config: { stiffness: 120, damping: 12 } }); const stampSpring = spring({ frame, fps, delay: marks.stampSlap || 45, config: { stiffness: 200, damping: 15 } }); return (<AbsoluteFill style={{ backgroundColor: '#FDFBEE', backgroundImage: 'radial-gradient(#E2E8F0 1px, transparent 0)', backgroundSize: '24px 24px' }}><div style={{ display: 'flex', width: '100%', height: '100%', alignItems: 'center', justifyContent: 'center' }}><div style={{ width: 600, height: 400, backgroundColor: 'white', border: '4px solid #000', borderRadius: 24, boxShadow: '8px 8px 0px rgba(0,0,0,0.15)', transform: `translateY(${(1 - cardSpring) * 100}px) rotate(-1.5deg)`, opacity: cardSpring, padding: 40, position: 'relative' }}><h1 style={{ margin: 0 }}>Logic Card</h1><div style={{ position: 'absolute', top: -30, right: -40, backgroundColor: '#F6AD55', border: '4px solid #000', borderRadius: 40, padding: '10px 30px', transform: `scale(${stampSpring}) rotate(8deg)`, boxShadow: '4px 4px 0px #000' }}><b>STAMP</b></div></div></div></AbsoluteFill>); } render(<CanvasScene marks={marks} />);"
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
