import React, { Component, useMemo } from 'react';
import { Series, AbsoluteFill, useCurrentFrame, interpolate, spring, useVideoConfig } from 'remotion';
import { LiveProvider, LiveError, LivePreview } from 'react-live';
import type { Scene } from '../types/scene';

const CANVAS_WIDTH = 1080;
const CANVAS_HEIGHT = 1920;
const MOBILE_SAFE_PADDING_X = 84;
const MOBILE_SAFE_PADDING_Y = 120;

type MobileTextVariant = 'headline' | 'title' | 'body' | 'caption' | 'label';

type FitBoxInput = {
  x?: number;
  y?: number;
  width?: number;
  height?: number;
  paddingX?: number;
  paddingY?: number;
};

function clamp(value: number, min: number, max: number): number {
  if (!Number.isFinite(value)) return min;
  return Math.min(max, Math.max(min, value));
}

function safeFrame(marks: Record<string, number>, key: string, fallback = 0): number {
  const value = marks?.[key];
  if (!Number.isFinite(value)) return Math.max(0, Math.round(fallback));
  return Math.max(0, Math.round(value));
}

function getOrderedMarks(
  marks: Record<string, number>,
  options?: { minGap?: number; fallbackOrder?: string[] }
): Record<string, number> {
  const minGap = Math.max(0, Math.round(options?.minGap ?? 0));
  const entries = Object.entries(marks ?? {})
    .filter(([, value]) => Number.isFinite(value))
    .sort((a, b) => {
      const frameDiff = a[1] - b[1];
      if (frameDiff !== 0) return frameDiff;

      const fallbackOrder = options?.fallbackOrder ?? [];
      const aIndex = fallbackOrder.indexOf(a[0]);
      const bIndex = fallbackOrder.indexOf(b[0]);
      if (aIndex !== -1 || bIndex !== -1) {
        if (aIndex === -1) return 1;
        if (bIndex === -1) return -1;
        return aIndex - bIndex;
      }

      return a[0].localeCompare(b[0]);
    });

  return entries.reduce<Record<string, number>>((acc, [key, value], index) => {
    const rounded = Math.max(0, Math.round(value));
    const previous = index === 0 ? rounded : Object.values(acc)[index - 1] ?? rounded;
    acc[key] = index === 0 ? rounded : Math.max(rounded, previous + minGap);
    return acc;
  }, {});
}

function fitBox(input: FitBoxInput) {
  const paddingX = Math.max(0, input.paddingX ?? MOBILE_SAFE_PADDING_X);
  const paddingY = Math.max(0, input.paddingY ?? MOBILE_SAFE_PADDING_Y);
  const width = clamp(input.width ?? CANVAS_WIDTH, 1, CANVAS_WIDTH - paddingX * 2);
  const height = clamp(input.height ?? CANVAS_HEIGHT, 1, CANVAS_HEIGHT - paddingY * 2);
  const x = clamp(input.x ?? paddingX, paddingX, CANVAS_WIDTH - paddingX - width);
  const y = clamp(input.y ?? paddingY, paddingY, CANVAS_HEIGHT - paddingY - height);

  return { x, y, width, height };
}

function createMobileTextStyle(
  variant: MobileTextVariant,
  overrides: React.CSSProperties = {}
): React.CSSProperties {
  const presets: Record<MobileTextVariant, React.CSSProperties> = {
    headline: { fontSize: 92, lineHeight: 1.08, fontWeight: 900, letterSpacing: '-0.04em' },
    title: { fontSize: 72, lineHeight: 1.12, fontWeight: 800, letterSpacing: '-0.03em' },
    body: { fontSize: 42, lineHeight: 1.32, fontWeight: 700 },
    caption: { fontSize: 34, lineHeight: 1.28, fontWeight: 700 },
    label: { fontSize: 30, lineHeight: 1.2, fontWeight: 800, letterSpacing: '0.02em' },
  };
  const minFontSizeByVariant: Record<MobileTextVariant, number> = {
    headline: 88,
    title: 64,
    body: 38,
    caption: 32,
    label: 28,
  };
  const requestedFontSize = Number(overrides.fontSize ?? presets[variant].fontSize);

  return {
    fontFamily:
      '"Alibaba PuHuiTi", "PingFang SC", "Hiragino Sans GB", "Microsoft YaHei", sans-serif',
    color: '#111827',
    wordBreak: 'break-word',
    overflowWrap: 'anywhere',
    ...presets[variant],
    ...overrides,
    fontSize: clamp(
      Number.isFinite(requestedFontSize) ? requestedFontSize : minFontSizeByVariant[variant],
      minFontSizeByVariant[variant],
      180
    ),
  };
}

const SafeArea: React.FC<{ children: React.ReactNode; style?: React.CSSProperties }> = ({
  children,
  style,
}) => (
  <div
    style={{
      position: 'absolute',
      left: MOBILE_SAFE_PADDING_X,
      right: MOBILE_SAFE_PADDING_X,
      top: MOBILE_SAFE_PADDING_Y,
      bottom: MOBILE_SAFE_PADDING_Y,
      overflow: 'hidden',
      ...style,
    }}
  >
    {children}
  </div>
);

// ── 代码清洗：去除 AI 可能注入的不合规语法 ─────────────────────────────────────
function sanitizeCode(raw: string): string {
  let code = raw;

  // 1. 去除 Markdown 代码围栏（如 ```jsx ... ``` 或 ```tsx ... ```）
  code = code.replace(/^```[\w]*\n?/gm, '').replace(/^```\n?/gm, '');

  // 2. 去除所有 import 语句（react-live 沙盒不支持模块导入）
  code = code.replace(/^import\s+.*?from\s+['"][^'"]+['"];?\s*$/gm, '');
  code = code.replace(/^import\s+['"][^'"]+['"];?\s*$/gm, '');

  // 3. 去除 export default / export const / export function 前缀
  code = code.replace(/^export\s+default\s+/gm, '');
  code = code.replace(/^export\s+(const|function|class|let|var)\s+/gm, '$1 ');

  // 4. 确保末尾有 render(...) 调用（如果代码没有的话，尝试推断主组件名再补上）
  const trimmed = code.trimEnd();
  if (!trimmed.match(/render\s*\(/)) {
    // 尝试找最后一个函数/const 组件名
    const matches = [...code.matchAll(/(?:function|const)\s+([A-Z][A-Za-z0-9]*)\s*(?:\(|\s*=\s*(?:\(|\())/g)];
    if (matches.length > 0) {
      const componentName = matches[matches.length - 1][1];
      code = code + `\n\nrender(<${componentName} marks={marks} />);`;
    }
  }

  return code.trim();
}

// ── 错误边界：防止单个分镜的渲染错误扩散到整个播放器 ──────────────────────────
interface ErrorBoundaryState {
  hasError: boolean;
  error: Error | null;
}

class SceneErrorBoundary extends Component<
  { children: React.ReactNode; sceneId: string },
  ErrorBoundaryState
> {
  constructor(props: { children: React.ReactNode; sceneId: string }) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { hasError: true, error };
  }

  render() {
    if (this.state.hasError) {
      return (
        <AbsoluteFill
          style={{
            backgroundColor: '#0f0f12',
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'center',
            padding: '24px',
          }}
        >
          <div
            style={{
              background: '#1a0a0a',
              border: '1px solid #7f1d1d',
              borderRadius: '8px',
              padding: '16px',
              maxWidth: '90%',
            }}
          >
            <div style={{ color: '#f87171', fontSize: '14px', fontWeight: 600, marginBottom: '8px' }}>
              ⚠ 分镜渲染错误：{this.props.sceneId}
            </div>
            <div
              style={{
                color: '#fca5a5',
                fontSize: '12px',
                fontFamily: 'monospace',
                whiteSpace: 'pre-wrap',
                wordBreak: 'break-all',
              }}
            >
              {this.state.error?.message}
            </div>
          </div>
        </AbsoluteFill>
      );
    }
    return this.props.children;
  }
}

// ── 沙盒引擎：把 marks 锚点与 Remotion API 注入 react-live ────────────────────
const EngineScene: React.FC<{ code: string; marks: Record<string, number>; sceneId: string }> = ({
  code,
  marks,
  sceneId,
}) => {
  const cleanCode = useMemo(() => sanitizeCode(code), [code]);

  // 将所有可用的 Remotion Hooks/API 以及 React 注入沙盒 scope
  const scope = useMemo(
    () => ({
      React,
      AbsoluteFill,
      useCurrentFrame,
      interpolate,
      spring,
      useVideoConfig,
      SafeArea,
      safeFrame,
      getOrderedMarks,
      fitBox,
      createMobileTextStyle,
      marks,
    }),
    [marks]
  );

  // 如果代码是空的或只有注释，显示占位符
  const isPlaceholder =
    !cleanCode ||
    cleanCode
      .split('\n')
      .every((l) => l.trim() === '' || l.trim().startsWith('//'));

  if (isPlaceholder) {
    return (
      <AbsoluteFill
        style={{
          backgroundColor: '#0d0d10',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
        }}
      >
        <div
          style={{
            color: '#6b7280',
            fontSize: '14px',
            fontFamily: 'monospace',
            textAlign: 'center',
          }}
        >
          <div style={{ marginBottom: '8px', fontSize: '24px' }}>⏳</div>
          <div>{sceneId}</div>
          <div style={{ fontSize: '11px', marginTop: '6px', color: '#374151' }}>等待代码生成...</div>
        </div>
      </AbsoluteFill>
    );
  }

  return (
    <LiveProvider code={cleanCode} scope={scope} noInline={true}>
      <LivePreview style={{ width: '100%', height: '100%' }} />
      <LiveError
        style={{
          position: 'absolute',
          inset: 0,
          backgroundColor: 'rgba(15,10,10,0.93)',
          color: '#f87171',
          padding: '20px',
          fontSize: '12px',
          fontFamily: 'monospace',
          whiteSpace: 'pre-wrap',
          overflow: 'auto',
          zIndex: 9999,
        }}
      />
    </LiveProvider>
  );
};

// ── 主视频容器 ────────────────────────────────────────────────────────────────
export const MainVideo: React.FC<{ scenes: Scene[] }> = ({ scenes }) => {
  return (
    <Series>
      {scenes.map((scene) => (
        <Series.Sequence key={scene.id} durationInFrames={scene.durationInFrames}>
          <SceneErrorBoundary sceneId={scene.id}>
            <EngineScene code={scene.code} marks={scene.marks} sceneId={scene.id} />
          </SceneErrorBoundary>
        </Series.Sequence>
      ))}
    </Series>
  );
};
