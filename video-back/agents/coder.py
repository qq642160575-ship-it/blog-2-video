from pydantic import BaseModel, Field

from models.get_model import get_model
from prompts.manager import PromptManager
example = """
function HandyScene({ marks }) {
  const frame = useCurrentFrame();
  
  // 基础动画变量
  const spr = (d = 0) => spring({ frame: frame - d, fps: 30, config: { damping: 12 } });
  
  // 浮动动画 (Idle Floating)
  const floatY = (speed = 1, amp = 10) => Math.sin(frame / (10 * speed)) * amp;
  const floatRot = (speed = 1.2, amp = 2) => Math.cos(frame / (12 * speed)) * amp;

  return (
    <AbsoluteFill style={{ 
      backgroundColor: '#FEF9E7',
      backgroundImage: 'radial-gradient(#dbcbb0 1.5px, transparent 1.5px)',
      backgroundSize: '48px 48px',
      justifyContent: 'center',
      alignItems: 'center',
      fontFamily: 'sans-serif'
    }}>
      {/* 1. 中心笑脸 - 最先出现 */}
      <div style={{
        transform: `scale(${spr(0)}) translateY(${floatY(1, 15)}px) rotate(${floatRot(1, 3)}deg)`,
        width: '240px',
        height: '240px',
        backgroundColor: '#4FC3F7',
        border: '6px solid #000',
        borderRadius: '120px',
        boxShadow: '12px 12px 0px 0px #000',
        display: 'flex',
        justifyContent: 'center',
        alignItems: 'center',
        fontSize: '120px',
        zIndex: 10
      }}>
        😊
      </div>

      {/* 2. 气泡 - 延迟出现 */}
      {frame > marks.showBubble && (
        <div style={{
          position: 'absolute',
          top: '32%',
          left: '52%',
          transform: `scale(${spr(marks.showBubble)}) translateY(${floatY(1.2, 10)}px) rotate(${5 + floatRot(0.8, 2)}deg)`,
          transformOrigin: 'bottom left',
          padding: '24px 48px',
          backgroundColor: '#FFD966',
          border: '6px solid #000',
          borderRadius: '30px',
          boxShadow: '12px 12px 0px 0px #000',
          fontSize: '56px',
          fontWeight: '900',
          color: '#000',
          whiteSpace: 'nowrap',
          zIndex: 20
        }}>
          Hello 大家好！
          {/* 气泡小尾巴 */}
          <div style={{
            position: 'absolute',
            bottom: '-28px',
            left: '40px',
            width: '0',
            height: '0',
            borderLeft: '20px solid transparent',
            borderRight: '20px solid transparent',
            borderTop: '30px solid #000'
          }} />
        </div>
      )}

      {/* 3. 日历卡片 - 最后出现 */}
      {frame > marks.showCard && (
        <div style={{
          position: 'absolute',
          bottom: '22%',
          right: '52%',
          transformOrigin: 'top right',
          transform: `scale(${spr(marks.showCard)}) translateY(${floatY(0.8, 12)}px) rotate(${-8 + floatRot(1.5, 4)}deg)`,
          padding: '40px',
          backgroundColor: '#FFF',
          border: '6px solid #000',
          borderRadius: '40px',
          boxShadow: '12px 12px 0px 0px #000',
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          gap: '20px',
          zIndex: 15
        }}>
          <div style={{ fontSize: '80px', filter: 'drop-shadow(4px 4px 0 #000)' }}>📅</div>
          <div style={{ fontSize: '40px', fontWeight: '900', color: '#000', letterSpacing: '-1px' }}>
            过去的三个月
          </div>
        </div>
      )}
    </AbsoluteFill>
  );
}

render(<HandyScene marks={marks} />);
"""


class Result(BaseModel):
    code: str = Field(..., description="生成的代码")

coder_agent = {
    "name": "coder-agent",
    "description": "负责将视觉协议转化为 Remotion React 代码",
    "model": get_model('cc'),  # 代码生成质量，尤其是复杂动效逻辑，目前最优 (claude-3-5-sonnet)
    "system_prompt": PromptManager().get_system_prompt('coder', example=example),
    "tools": None, # [code_sandbox_validator, tailwind_linter] placeholders
    "response_format": Result
}
print(coder_agent.get('system_prompt'))