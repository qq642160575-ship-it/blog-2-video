import { useEffect, useRef } from 'react';
import type { RefObject } from 'react';
import type { PlayerRef } from '@remotion/player';
import type { Scene } from '../types/scene';

/**
 * 响应 activeSceneId 变化，自动将 Player seek 到对应起始帧。
 * 解除 Timeline 对 playerRef 的直接命令式依赖。
 */
export function usePlayerControl(
  playerRef: RefObject<PlayerRef | null>,
  scenes: Scene[],
  activeSceneId: string
) {
  // 用 ref 记录上一次的 activeSceneId，初次挂载不 seek（避免 autoPlay 被打断）
  const prevIdRef = useRef<string | null>(null);

  useEffect(() => {
    if (prevIdRef.current === null) {
      prevIdRef.current = activeSceneId;
      return;
    }
    if (prevIdRef.current === activeSceneId) return;
    prevIdRef.current = activeSceneId;

    const idx = scenes.findIndex((s) => s.id === activeSceneId);
    if (idx === -1) return;

    const startFrame = scenes
      .slice(0, idx)
      .reduce((sum, s) => sum + s.durationInFrames, 0);

    playerRef.current?.seekTo(startFrame);
  }, [activeSceneId, scenes, playerRef]);
}
