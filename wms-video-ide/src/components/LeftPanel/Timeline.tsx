import React, { useCallback } from 'react';
import { useIdeStore } from '../../store/useIdeStore';
import { SceneCard } from './SceneCard';

/**
 * Timeline 节奏轴。
 * - 精确订阅 scenes / activeSceneId，不拉取无关 store 字段
 * - onSelect 仅调用 setActiveScene，seek 逻辑由 usePlayerControl 响应式处理
 */
export const Timeline: React.FC = () => {
  const scenes = useIdeStore((s) => s.scenes);
  const activeSceneId = useIdeStore((s) => s.activeSceneId);
  const setActiveScene = useIdeStore((s) => s.setActiveScene);
  const updateSceneDuration = useIdeStore((s) => s.updateSceneDuration);
  const updateSceneMark = useIdeStore((s) => s.updateSceneMark);

  const handleSelect = useCallback(
    (id: string) => setActiveScene(id),
    [setActiveScene]
  );

  const handleDurationChange = useCallback(
    (id: string, frames: number) => updateSceneDuration(id, frames),
    [updateSceneDuration]
  );

  const handleMarkChange = useCallback(
    (sceneId: string, markKey: string, newFrame: number) =>
      updateSceneMark(sceneId, markKey, newFrame),
    [updateSceneMark]
  );

  return (
    <div>
      <h3 className="text-[10px] text-gray-500 font-bold uppercase tracking-wider mb-2">
        Timeline 节奏轴
      </h3>
      <div className="space-y-2">
        {scenes.map((scene) => (
          <SceneCard
            key={scene.id}
            scene={scene}
            isActive={scene.id === activeSceneId}
            onSelect={handleSelect}
            onDurationChange={handleDurationChange}
            onMarkChange={handleMarkChange}
          />
        ))}
      </div>
    </div>
  );
};
