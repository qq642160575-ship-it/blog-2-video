import { create } from 'zustand';
import type { Scene } from '../types/scene';

export type AiStatus = 'idle' | 'generating' | 'error';

export interface IdeState {
  // ── 数据层 ──
  sourceText: string;
  scenes: Scene[];
  activeSceneId: string;
  aiStatus: AiStatus;

  // ── Actions ──
  setSourceText: (text: string) => void;
  setActiveScene: (id: string) => void;
  setAiStatus: (status: AiStatus) => void;
  updateSceneCode: (id: string, newCode: string) => void;
  updateSceneDuration: (id: string, durationInFrames: number) => void;
  updateSceneMark: (sceneId: string, markKey: string, newFrame: number) => void;
  updateSceneScript: (id: string, newScript: string) => void;
}

const MOCK_SCENES: Scene[] = [
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
];

const DEFAULT_SOURCE_TEXT =
  '在 WMS 系统中，入库单的状态流转非常关键。从初始的 CREATED 到 ARRIVED。每一步都需要校验库存掩码，防止数据并发冲突。';

export const useIdeStore = create<IdeState>((set) => ({
  sourceText: DEFAULT_SOURCE_TEXT,
  scenes: MOCK_SCENES,
  activeSceneId: MOCK_SCENES[0].id,
  aiStatus: 'idle',

  setSourceText: (text) => set({ sourceText: text }),
  setActiveScene: (id) => set({ activeSceneId: id }),
  setAiStatus: (status) => set({ aiStatus: status }),

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
