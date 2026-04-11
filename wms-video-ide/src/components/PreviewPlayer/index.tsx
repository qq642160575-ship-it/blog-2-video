import React, { useRef, useMemo } from 'react';
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
  const aiStatus = useIdeStore((s) => s.aiStatus);
  const inputProps = useMemo(() => ({ scenes }), [scenes]);
  const hasScenes = scenes.length > 0;

  usePlayerControl(playerRef, scenes, activeSceneId);

  return (
    <div className="w-[30%] flex flex-col border-r border-gray-800 bg-black">
      <div className="px-3 py-2.5 border-b border-gray-800 flex items-center justify-between bg-[#18181b] flex-shrink-0">
        <div className="flex items-center gap-2 text-xs text-gray-400">
          <PlaySquare className="w-3.5 h-3.5 text-green-400" />
          <span className="font-semibold text-[12px]">预览</span>
        </div>
        <div className="text-[11px] px-2 py-0.5 bg-gray-800/60 rounded text-gray-500 font-mono">
          {hasScenes ? `${(totalFrames / 30).toFixed(1)}s` : '未生成'}
        </div>
      </div>

      <div className="flex-1 flex items-center justify-center p-3 overflow-hidden">
        {!hasScenes ? (
          <div className="w-full h-full rounded-lg border border-dashed border-gray-800 bg-[#0f0f12] flex items-center justify-center p-6">
            <div className="max-w-[220px] text-center">
              <p className="text-sm text-gray-300">
                {aiStatus === 'generating' ? '正在准备预览内容...' : '预览将在生成分镜后显示'}
              </p>
              <p className="mt-2 text-[12px] text-gray-500">
                为了减少干扰，未开始前这里不会自动播放示例内容。
              </p>
            </div>
          </div>
        ) : (
          <div
            className="relative shadow-2xl shadow-purple-900/20 border border-gray-800 rounded-lg overflow-hidden"
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

      <div className="px-3 py-1 border-t border-gray-800/60 flex items-center justify-end bg-[#0e0e11]">
        <span className="text-[10px] text-gray-700 font-mono tracking-wide">Remotion · 30fps</span>
      </div>
    </div>
  );
};
