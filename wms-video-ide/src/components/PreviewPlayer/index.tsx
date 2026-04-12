import React, { useMemo, useRef } from 'react';
import { Player } from '@remotion/player';
import type { PlayerRef } from '@remotion/player';
import { PlaySquare } from 'lucide-react';
import { useIdeStore } from '../../store/useIdeStore';
import { selectTotalFrames } from '../../store/selectors';
import { usePlayerControl } from '../../hooks/usePlayerControl';
import { MainVideo } from '../MainVideo';

export const PreviewPlayer: React.FC = () => {
  const playerRef = useRef<PlayerRef>(null);
  const scenes = useIdeStore((s) => s.scenes);
  const activeSceneId = useIdeStore((s) => s.activeSceneId);
  const totalFrames = useIdeStore(selectTotalFrames);
  const inputProps = useMemo(() => ({ scenes }), [scenes]);
  const hasScenes = scenes.length > 0;

  usePlayerControl(playerRef, scenes, activeSceneId);

  return (
    <div className="flex w-[28%] flex-col border-r border-gray-800 bg-black">
      <div className="flex flex-shrink-0 items-center justify-between border-b border-gray-800 bg-[#18181b] px-3 py-2.5">
        <div className="flex items-center gap-2 text-xs text-gray-400">
          <PlaySquare className="h-3.5 w-3.5 text-emerald-400" />
          <span className="text-[12px] font-semibold">预览</span>
        </div>
        <div className="rounded bg-gray-800/60 px-2 py-0.5 font-mono text-[11px] text-gray-500">
          {hasScenes ? `${(totalFrames / 30).toFixed(1)}s` : '等待生成'}
        </div>
      </div>

      <div className="flex flex-1 items-center justify-center overflow-hidden p-3">
        {!hasScenes ? (
          <div className="flex h-full w-full items-center justify-center rounded-lg border border-dashed border-gray-800 bg-[#0f0f12] p-6">
            <div className="max-w-[240px] text-center">
              <p className="text-sm text-gray-300">完成步骤 2 后，这里会显示视频预览。</p>
              <p className="mt-2 text-[12px] text-gray-500">
                选择左侧镜头时，播放器会自动跳转到对应位置。
              </p>
            </div>
          </div>
        ) : (
          <div
            className="relative overflow-hidden rounded-lg border border-gray-800 shadow-2xl shadow-violet-900/20"
            style={{ width: '100%', aspectRatio: '1080/1920', maxHeight: 'calc(100% - 48px)' }}
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
            />
          </div>
        )}
      </div>

      <div className="flex items-center justify-end border-t border-gray-800/60 bg-[#0e0e11] px-3 py-1">
        <span className="font-mono text-[10px] tracking-wide text-gray-700">Remotion · 30fps</span>
      </div>
    </div>
  );
};
