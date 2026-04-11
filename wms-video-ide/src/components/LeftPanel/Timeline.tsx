import React, { useCallback, useState } from 'react';
import { useIdeStore } from '../../store/useIdeStore';
import { SceneCard } from './SceneCard';
import { ChevronDown, ChevronUp } from 'lucide-react';

export const Timeline: React.FC = () => {
  const scenes = useIdeStore((s) => s.scenes);
  const activeSceneId = useIdeStore((s) => s.activeSceneId);
  const setActiveScene = useIdeStore((s) => s.setActiveScene);
  const updateSceneDuration = useIdeStore((s) => s.updateSceneDuration);
  const updateSceneMark = useIdeStore((s) => s.updateSceneMark);
  const aiStatus = useIdeStore((s) => s.aiStatus);
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

  const isGenerating = aiStatus === 'generating';

  return (
    <div className="border border-gray-800 rounded-lg overflow-hidden flex-shrink-0 bg-[#141416]">
      <button
        onClick={() => setIsOpen((v) => !v)}
        className="w-full flex items-center justify-between px-4 py-3 bg-[#1c1c1f] hover:bg-[#232326] transition-colors"
      >
        <div className="flex items-center gap-2">
          <span className="flex items-center justify-center w-5 h-5 rounded-full bg-green-500/10 text-green-400 text-[10px] font-bold">3</span>
          <h3 className="text-xs text-gray-300 font-bold tracking-wide">Timeline 分镜轴</h3>
        </div>
        {isOpen ? <ChevronUp className="w-4 h-4 text-gray-500" /> : <ChevronDown className="w-4 h-4 text-gray-500" />}
      </button>

      {isOpen && (
        <div className="p-3 border-t border-gray-800 space-y-2">
          {scenes.length === 0 ? (
            <div className="rounded-lg border border-dashed border-gray-700 bg-[#111113] px-4 py-6 text-center">
              <p className="text-sm text-gray-300">
                {isGenerating ? '正在生成分镜，请稍候...' : 'Timeline 尚未生成'}
              </p>
              <p className="text-[12px] mt-2 text-gray-500">
                {oralScript
                  ? '点击上一步的“导入 Timeline 并生成视频”后，这里会出现分镜。'
                  : '先完成口语稿生成，再进入 Timeline 阶段。'}
              </p>
            </div>
          ) : (
            scenes.map((scene) => (
              <SceneCard
                key={scene.id}
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
