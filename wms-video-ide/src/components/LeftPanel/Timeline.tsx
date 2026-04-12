import React, { useCallback, useState } from 'react';
import { ChevronDown, ChevronUp } from 'lucide-react';
import { useIdeStore } from '../../store/useIdeStore';
import { SceneCard } from './SceneCard';

export const Timeline: React.FC = () => {
  const scenes = useIdeStore((s) => s.scenes);
  const activeSceneId = useIdeStore((s) => s.activeSceneId);
  const setActiveScene = useIdeStore((s) => s.setActiveScene);
  const updateSceneDuration = useIdeStore((s) => s.updateSceneDuration);
  const updateSceneMark = useIdeStore((s) => s.updateSceneMark);
  const oralScript = useIdeStore((s) => s.oralScript);
  const [isOpen, setIsOpen] = useState(true);

  const handleSelect = useCallback((id: string) => setActiveScene(id), [setActiveScene]);
  const handleDurationChange = useCallback(
    (id: string, frames: number) => updateSceneDuration(id, frames),
    [updateSceneDuration]
  );
  const handleMarkChange = useCallback(
    (sceneId: string, markKey: string, newFrame: number) =>
      updateSceneMark(sceneId, markKey, newFrame),
    [updateSceneMark]
  );

  if (!oralScript.trim() && scenes.length === 0) {
    return null;
  }

  return (
    <div className="flex min-h-0 flex-col overflow-hidden rounded-lg border border-gray-800 bg-[#141416]">
      <button
        onClick={() => setIsOpen((value) => !value)}
        className="flex w-full flex-shrink-0 items-center justify-between bg-[#1c1c1f] px-4 py-3 transition-colors hover:bg-[#232326]"
      >
        <div className="flex items-center gap-2">
          <span className="flex h-5 w-5 items-center justify-center rounded-full bg-emerald-500/10 text-[10px] font-bold text-emerald-400">
            3
          </span>
          <h3 className="text-xs font-bold tracking-wide text-gray-300">Timeline 分镜</h3>
        </div>
        {isOpen ? (
          <ChevronUp className="h-4 w-4 text-gray-500" />
        ) : (
          <ChevronDown className="h-4 w-4 text-gray-500" />
        )}
      </button>

      {isOpen && (
        <div className="max-h-[52vh] min-h-0 space-y-2 overflow-y-auto overscroll-contain border-t border-gray-800 p-3 pr-2">
          {scenes.length === 0 ? (
            <div className="rounded-lg border border-dashed border-gray-700 bg-[#111113] px-4 py-6 text-center">
              <p className="text-sm text-gray-300">口播稿已就绪，等待生成分镜。</p>
              <p className="mt-2 text-[12px] text-gray-500">
                点击上一步中的“生成分镜与代码”后，这里会出现可编辑的镜头列表。
              </p>
            </div>
          ) : (
            scenes.map((scene, index) => (
              <SceneCard
                key={scene.id}
                index={index}
                scene={scene}
                isActive={scene.id === activeSceneId}
                onSelect={handleSelect}
                onDurationChange={handleDurationChange}
                onMarkChange={handleMarkChange}
              />
            ))
          )}
        </div>
      )}
    </div>
  );
};
