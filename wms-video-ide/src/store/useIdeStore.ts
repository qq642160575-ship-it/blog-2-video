import { create } from 'zustand';
import type { Scene } from '../types/scene';

export type AiStatus = 'idle' | 'generating' | 'error';
export type RewriteStatus = 'idle' | 'generating' | 'error' | 'success';

export interface IdeState {
  // ── 数据层 ──
  sourceText: string;
  oralScript: string;
  scenes: Scene[];
  activeSceneId: string;
  aiStatus: AiStatus;
  rewriteStatus: RewriteStatus;

  // ── Actions ──
  setSourceText: (text: string) => void;
  setOralScript: (text: string) => void;
  setActiveScene: (id: string) => void;
  setAiStatus: (status: AiStatus) => void;
  setRewriteStatus: (status: RewriteStatus) => void;
  updateSceneCode: (id: string, newCode: string) => void;
  updateSceneDuration: (id: string, durationInFrames: number) => void;
  updateSceneMark: (sceneId: string, markKey: string, newFrame: number) => void;
  updateSceneScript: (id: string, newScript: string) => void;
}

const MOCK_SCENES: Scene[] = [
  {
    id: 'scene-seq',
    durationInFrames: 420,
    componentType: 'SequenceDiagram',
    script: '入库请求从客户端发出，经过API网关鉴权，WMS服务处理业务逻辑，最后写入数据库完成持久化。',
    marks: { msg1: 30, msg2: 90, msg3: 150, msg4: 210, msg5: 270, msg6: 330 },
    code: `function SequenceDiagram({ marks }) {
  const frame = useCurrentFrame();

  const W = 1080;
  const H = 1920;

  const participants = [
    { id: 'client',  label: '客户端',   color: '#6366F1' },
    { id: 'gateway', label: 'API 网关', color: '#F59E0B' },
    { id: 'wms',     label: 'WMS 服务', color: '#10B981' },
    { id: 'db',      label: '数据库',   color: '#EF4444' },
  ];

  const messages = [
    { from: 0, to: 1, label: 'POST /inbound/create', mark: 'msg1', color: '#A5B4FC' },
    { from: 1, to: 2, label: '鉴权 + 转发请求',       mark: 'msg2', color: '#FCD34D' },
    { from: 2, to: 3, label: 'INSERT inbound_order',  mark: 'msg3', color: '#6EE7B7' },
    { from: 3, to: 2, label: 'OK rowId=8821',         mark: 'msg4', color: '#FCA5A5', dashed: true },
    { from: 2, to: 1, label: '状态: CREATED',          mark: 'msg5', color: '#FCA5A5', dashed: true },
    { from: 1, to: 0, label: '{ code:0, id:8821 }',   mark: 'msg6', color: '#FCA5A5', dashed: true },
  ];

  const PAD_X = 80;
  const BOX_W = 180;
  const BOX_H = 72;
  const TOP_Y = 140;
  const LIFE_BOTTOM = H - 160;
  const MSG_LABEL_OFFSET = -22;

  const colW = (W - PAD_X * 2) / (participants.length - 1);
  const cx = (i) => PAD_X + i * colW;

  const titleOpacity = interpolate(frame, [0, 20], [0, 1], { extrapolateRight: 'clamp' });

  const headerScale = (i) =>
    spring({ fps: 30, frame: frame - i * 8, config: { damping: 14, stiffness: 120 } });

  const lifeLineH = interpolate(
    frame, [0, 60], [0, LIFE_BOTTOM - TOP_Y - BOX_H / 2],
    { extrapolateRight: 'clamp' }
  );

  const msgAnim = (msg) => {
    const startFrame = marks[msg.mark];
    const elapsed = frame - startFrame;
    const fromX = cx(msg.from);
    const toX = cx(msg.to);
    const progress = interpolate(elapsed, [0, 18], [0, 1], { extrapolateRight: 'clamp' });
    const currentX = fromX + (toX - fromX) * progress;
    const labelOpacity = interpolate(elapsed, [14, 22], [0, 1], { extrapolateRight: 'clamp' });
    return { fromX, toX, currentX, progress, labelOpacity, visible: elapsed >= 0 };
  };

  const msgY = (index) => TOP_Y + BOX_H / 2 + 80 + index * 120;

  const arrowHead = (x1, y, x2) => {
    const dir = x2 > x1 ? 1 : -1;
    const tip = x2;
    return \`\${tip},\${y} \${tip - dir * 18},\${y - 10} \${tip - dir * 18},\${y + 10}\`;
  };

  return (
    <AbsoluteFill style={{ backgroundColor: '#0F172A' }}>
      <svg width={W} height={H} viewBox={\`0 0 \${W} \${H}\`}>

        {/* 标题 */}
        <text
          x={W / 2} y={72}
          textAnchor="middle" fill="white"
          fontSize="52" fontWeight="bold" fontFamily="sans-serif"
          opacity={titleOpacity}
        >
          入库单创建时序图
        </text>

        {/* 参与者方块 + 生命线 */}
        {participants.map((p, i) => {
          const x = cx(i);
          const scale = headerScale(i);
          return (
            <g key={p.id}
              transform={\`translate(\${x},\${TOP_Y + BOX_H / 2}) scale(\${scale}) translate(\${-x},\${-(TOP_Y + BOX_H / 2)})\`}
            >
              <rect
                x={x - BOX_W / 2} y={TOP_Y}
                width={BOX_W} height={BOX_H} rx="12"
                fill={p.color} fillOpacity="0.15"
                stroke={p.color} strokeWidth="2.5"
              />
              <text
                x={x} y={TOP_Y + BOX_H / 2 + 8}
                textAnchor="middle" fill={p.color}
                fontSize="32" fontWeight="bold" fontFamily="sans-serif"
              >
                {p.label}
              </text>
              <line
                x1={x} y1={TOP_Y + BOX_H}
                x2={x} y2={TOP_Y + BOX_H + lifeLineH}
                stroke={p.color} strokeWidth="2"
                strokeOpacity="0.35" strokeDasharray="8 6"
              />
            </g>
          );
        })}

        {/* 消息箭头 */}
        {messages.map((msg, index) => {
          const anim = msgAnim(msg);
          if (!anim.visible) return null;
          const y = msgY(index);
          const { fromX, toX, currentX, labelOpacity } = anim;
          return (
            <g key={msg.mark}>
              <line
                x1={fromX} y1={y} x2={currentX} y2={y}
                stroke={msg.color} strokeWidth="3"
                strokeDasharray={msg.dashed ? '10 6' : 'none'}
                strokeLinecap="round"
              />
              {anim.progress > 0.85 && (
                <polygon points={arrowHead(fromX, y, toX)} fill={msg.color} />
              )}
              <rect
                x={Math.min(fromX, toX) + Math.abs(toX - fromX) * 0.18}
                y={y + MSG_LABEL_OFFSET - 24}
                width={Math.abs(toX - fromX) * 0.64} height={36}
                rx="6" fill="#1E293B" opacity={labelOpacity * 0.85}
              />
              <text
                x={(fromX + toX) / 2} y={y + MSG_LABEL_OFFSET}
                textAnchor="middle" fill={msg.color}
                fontSize="26" fontFamily="monospace"
                opacity={labelOpacity}
              >
                {msg.label}
              </text>
            </g>
          );
        })}

        {/* 底部参与者方块 */}
        {participants.map((p, i) => {
          const x = cx(i);
          const bottomY = LIFE_BOTTOM;
          const appear = interpolate(frame - 20, [0, 20], [0, 1], { extrapolateRight: 'clamp' });
          return (
            <g key={\`bottom-\${p.id}\`} opacity={appear}>
              <rect
                x={x - BOX_W / 2} y={bottomY}
                width={BOX_W} height={BOX_H} rx="12"
                fill={p.color} fillOpacity="0.15"
                stroke={p.color} strokeWidth="2.5"
              />
              <text
                x={x} y={bottomY + BOX_H / 2 + 8}
                textAnchor="middle" fill={p.color}
                fontSize="32" fontWeight="bold" fontFamily="sans-serif"
              >
                {p.label}
              </text>
            </g>
          );
        })}

      </svg>
    </AbsoluteFill>
  );
}

render(<SequenceDiagram marks={marks} />);`,
  },
  {
    id: 'scene-1',
    durationInFrames: 150,
    componentType: 'HighlightCard',
    script: '做 WMS 的朋友都知道，入库单的状态流转要是乱了，仓库就得炸锅。',
    marks: { boom: 90 },
    code: `function HighlightCard({ title, icon, themeColor, marks }) {
  const frame = useCurrentFrame();
  const scale = spring({ fps: 30, frame, config: { damping: 12 } });
  const opacity = interpolate(frame, [0, 15], [0, 1], { extrapolateRight: 'clamp' });

  // 在 boom 标记点产生震动效果 (Camera Shake)
  const shakeFrame = frame - marks.boom;
  const isShaking = shakeFrame > 0 && shakeFrame < 20;
  const offsetX = isShaking ? Math.sin(shakeFrame * 3) * 30 : 0;
  const offsetY = isShaking ? Math.cos(shakeFrame * 5) * 20 : 0;
  const shadowColor = isShaking ? 'rgba(239, 68, 68, 0.8)' : 'rgba(0,0,0,0.5)';

  return (
    <AbsoluteFill style={{ backgroundColor: '#111827', justifyContent: 'center', alignItems: 'center' }}>
      <div style={{
        transform: \`scale(\${scale}) translate(\${offsetX}px, \${offsetY}px)\`,
        opacity,
        backgroundColor: themeColor,
        padding: '60px 100px', borderRadius: '30px', color: 'white',
        boxShadow: \`0 25px 50px -12px \${shadowColor}\`,
        display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '40px',
        transition: 'box-shadow 0.1s'
      }}>
        <span style={{ fontSize: '120px' }}>{isShaking ? '💥' : icon}</span>
        <span style={{ fontSize: '64px', fontWeight: 'bold' }}>{title}</span>
      </div>
    </AbsoluteFill>
  );
}

render(
  <HighlightCard
    title="WMS 核心：入库状态流转"
    icon="📦"
    themeColor="#FF5733"
    marks={marks}
  />
);`,
  },
  {
    id: 'scene-2',
    durationInFrames: 300,
    componentType: 'FlowChart',
    script: '咱们看这三步：先是创建，接着到货，最后上架。注意中间的防并发。',
    marks: { node1: 30, node2: 75, node3: 120, highlight: 180 },
    code: `function FlowChart({ nodes, marks }) {
  const frame = useCurrentFrame();

  return (
    <AbsoluteFill style={{ backgroundColor: '#111827', justifyContent: 'center', alignItems: 'center', flexDirection: 'column' }}>
      <h2 style={{ color: 'white', fontSize: '60px', marginBottom: '80px' }}>状态流转架构</h2>
      <div style={{ display: 'flex', gap: '40px', alignItems: 'center', flexDirection: 'column' }}>
        {nodes.map((node, index) => {
          const markKey = \`node\${index + 1}\`;
          const delay = marks[markKey] || 0;
          const nodeScale = spring({ fps: 30, frame: frame - delay, config: { damping: 14 } });
          const opacity = interpolate(frame - delay, [0, 10], [0, 1], { extrapolateRight: 'clamp' });
          const isMask = index === 1 && marks.highlight;

          return (
            <React.Fragment key={node}>
              <div style={{
                transform: \`scale(\${nodeScale})\`, opacity, padding: '40px 80px',
                backgroundColor: '#374151', color: 'white', borderRadius: '20px',
                fontSize: '48px', fontWeight: 'bold', border: '4px solid #4B5563',
              }}>
                {node}
              </div>
              {index < nodes.length - 1 && (
                <>
                  {isMask && (
                    <div style={{
                      transform: \`scale(\${spring({ fps: 30, frame: frame - marks.highlight })})\`,
                      backgroundColor: '#FCA5A5', color: '#991B1B', padding: '20px 40px',
                      borderRadius: '12px', fontSize: '36px', fontWeight: 'bold',
                      boxShadow: '0 0 40px rgba(252, 165, 165, 0.4)', margin: '10px 0'
                    }}>
                      🔒 库存掩码校验
                    </div>
                  )}
                  {!isMask && <div style={{ color: '#9CA3AF', fontSize: '60px', opacity, margin: '10px 0' }}>⬇</div>}
                </>
              )}
            </React.Fragment>
          );
        })}
      </div>
    </AbsoluteFill>
  );
}

render(<FlowChart nodes={["创建单据", "货车到站", "完成上架"]} marks={marks} />);`,
  },
  {
    id: 'scene-handy',
    durationInFrames: 300,
    componentType: 'HandyScene',
    script: '大家好，欢迎来到我们的视频工作台！过去三个月，我们在这里记录了 WMS 系统的每一次成长。',
    marks: { "showBubble": 0, "showCard": 30 },
    code: `function HandyScene({ marks }) {
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
        transform: \`scale(\${spr(0)}) translateY(\${floatY(1, 15)}px) rotate(\${floatRot(1, 3)}deg)\`,
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
          transform: \`scale(\${spr(marks.showBubble)}) translateY(\${floatY(1.2, 10)}px) rotate(\${5 + floatRot(0.8, 2)}deg)\`,
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
          transform: \`scale(\${spr(marks.showCard)}) translateY(\${floatY(0.8, 12)}px) rotate(\${-8 + floatRot(1.5, 4)}deg)\`,
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

render(<HandyScene marks={marks} />);`,
  },
];

const DEFAULT_SOURCE_TEXT =
  '在 WMS 系统中，入库单的状态流转非常关键。从初始的 CREATED 到 ARRIVED。每一步都需要校验库存掩码，防止数据并发冲突。';

export const useIdeStore = create<IdeState>((set) => ({
  sourceText: DEFAULT_SOURCE_TEXT,
  oralScript: '',
  scenes: MOCK_SCENES,
  activeSceneId: MOCK_SCENES[0].id,
  aiStatus: 'idle',
  rewriteStatus: 'idle',

  setSourceText: (text) => set({ sourceText: text }),
  setOralScript: (text) => set({ oralScript: text }),
  setActiveScene: (id) => set({ activeSceneId: id }),
  setAiStatus: (status) => set({ aiStatus: status }),
  setRewriteStatus: (status) => set({ rewriteStatus: status }),

  updateSceneCode: (id, newCode) =>
    set((state) => ({
      scenes: state.scenes.map((s) => (s.id === id ? { ...s, code: newCode } : s)),
    })),

  updateSceneDuration: (id, durationInFrames) =>
    set((state) => ({
      scenes: state.scenes.map((s) => (s.id === id ? { ...s, durationInFrames } : s)),
    })),

  updateSceneMark: (sceneId, markKey, newFrame) =>
    set((state) => ({
      scenes: state.scenes.map((s) =>
        s.id === sceneId ? { ...s, marks: { ...s.marks, [markKey]: newFrame } } : s
      ),
    })),

  updateSceneScript: (id, newScript) =>
    set((state) => ({
      scenes: state.scenes.map((s) => (s.id === id ? { ...s, script: newScript } : s)),
    })),
}));
