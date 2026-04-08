import React, { useRef, useMemo } from 'react';
import { Player } from '@remotion/player';
import type { PlayerRef } from '@remotion/player';
import { PlaySquare } from 'lucide-react';
import { useIdeStore } from '../../store/useIdeStore';
import { selectTotalFrames } from '../../store/selectors';
import { usePlayerControl } from '../../hooks/usePlayerControl';
import { MainVideo } from '../MainVideo';

/**
 * Remotion Player 封装。
 *
 * 修正点：
 * 1. inputProps 用 useMemo 稳定引用，防止 scenes 引用变化导致 Player 无效重建
 * 2. seek 逻辑通过 usePlayerControl hook 响应式处理，不再由外部命令式触发
 * 3. 精确订阅 scenes / activeSceneId / totalFrames，不拉取无关字段
 */
export const PreviewPlayer: React.FC = () => {
  const playerRef = useRef<PlayerRef>(null);
  const scenes = useIdeStore((s) => s.scenes);
  const activeSceneId = useIdeStore((s) => s.activeSceneId);
  const totalFrames = useIdeStore(selectTotalFrames);

  // 响应 activeSceneId 变化自动 seek
  usePlayerControl(playerRef, scenes, activeSceneId);

  // 稳定 inputProps 引用，防止 Player 因每次渲染产生的新对象而重建
  const inputProps = useMemo(() => ({ scenes }), [scenes]);

  return (
    <div className="w-[35%] flex flex-col border-r border-gray-800 bg-black">
      {/* 顶栏 */}
      <div className="px-4 py-3 border-b border-gray-800 flex items-center justify-between bg-[#18181b] flex-shrink-0">
        <div className="flex items-center gap-2 text-xs text-gray-300">
          <PlaySquare className="w-4 h-4 text-green-400" />
          <span className="font-semibold">Remotion Engine</span>
        </div>
        <div className="text-[10px] px-2 py-1 bg-gray-800 rounded text-gray-400 font-mono">
          {(totalFrames / 30).toFixed(1)}s • 30FPS
        </div>
      </div>

      {/* Player 区域 */}
      <div className="flex-1 flex items-center justify-center p-4 overflow-hidden">
        <div
          className="relative shadow-2xl shadow-purple-900/20 border border-gray-800 rounded-lg overflow-hidden"
          style={{ height: '100%', aspectRatio: '1080/1920', maxHeight: '100%' }}
        >
          <Player
            ref={playerRef}
            component={MainVideo}
            inputProps={inputProps}
            durationInFrames={Math.max(1, totalFrames)}
            fps={30}
            compositionWidth={1080}
            compositionHeight={1920}
            style={{ width: '100%', height: '100%' }}
            controls
            autoPlay
          />
          <div className="absolute top-3 right-3 bg-black/60 backdrop-blur-sm text-white text-[9px] px-1.5 py-0.5 rounded border border-white/10 font-mono pointer-events-none">
            🔴 LIVE
          </div>
        </div>
      </div>
    </div>
  );
};
