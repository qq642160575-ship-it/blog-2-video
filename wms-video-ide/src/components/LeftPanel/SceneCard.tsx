import React, { useCallback } from 'react';
import { Clock } from 'lucide-react';
import type { Scene } from '../../types/scene';
import { DraggableMark } from './DraggableMark';

interface SceneCardProps {
  scene: Scene;
  isActive: boolean;
  onSelect: (id: string) => void;
  onDurationChange: (id: string, frames: number) => void;
  onMarkChange: (sceneId: string, markKey: string, newFrame: number) => void;
}

/**
 * 单个场景卡片。React.memo 包裹，只有 scene / isActive 变化才重渲染。
 */
export const SceneCard: React.FC<SceneCardProps> = React.memo(
  ({ scene, isActive, onSelect, onDurationChange, onMarkChange }) => {
    const handleDurationChange = useCallback(
      (e: React.ChangeEvent<HTMLInputElement>) => {
        onDurationChange(scene.id, Math.max(1, Number(e.target.value)) * 30);
      },
      [scene.id, onDurationChange]
    );

    const handleClick = useCallback(() => {
      onSelect(scene.id);
    }, [scene.id, onSelect]);

    return (
      <div
        onClick={handleClick}
        className={`border rounded-md transition-all relative overflow-hidden flex flex-col cursor-pointer ${
          isActive
            ? 'border-purple-500/50 bg-purple-500/10'
            : 'border-gray-800 bg-[#0e0e11] hover:border-gray-700'
        }`}
      >
        {/* 左侧激活条 */}
        {isActive && (
          <div className="absolute left-0 top-0 bottom-0 w-0.5 bg-purple-500" />
        )}

        <div className="px-3 pt-2.5 pb-2">
          <div className="flex justify-between items-center mb-1.5">
            {/* 时长编辑 */}
            <div
              className="flex items-center gap-1 bg-gray-900 rounded px-1.5 py-0.5 border border-gray-700"
              onClick={(e) => e.stopPropagation()}
            >
              <Clock className="w-2.5 h-2.5 text-gray-400" />
              <input
                type="number"
                value={scene.durationInFrames / 30}
                onChange={handleDurationChange}
                className="w-7 bg-transparent text-[10px] text-center text-gray-300 outline-none font-mono"
              />
              <span className="text-[9px] text-gray-500">s</span>
            </div>
            <span
              className={`text-[9px] px-1.5 py-0.5 rounded ${
                isActive
                  ? 'text-purple-300 bg-purple-500/20'
                  : 'text-gray-600 bg-gray-800'
              }`}
            >
              {scene.componentType}
            </span>
          </div>

          {/* 台词预览（截断 28 字） */}
          <p
            className={`text-[11px] leading-relaxed truncate ${
              isActive ? 'text-purple-200' : 'text-gray-600'
            }`}
          >
            {scene.script.length > 28 ? scene.script.slice(0, 28) + '…' : scene.script}
          </p>
        </div>

        {/* Rhythm Strip */}
        <div className="h-5 bg-black/40 border-t border-gray-800/50 relative rhythm-track">
          {/* 秒数网格 */}
          <div className="absolute inset-0 flex pointer-events-none">
            {Array.from({
              length: Math.max(1, Math.floor(scene.durationInFrames / 30)),
            }).map((_, i) => (
              <div key={i} className="flex-1 border-r border-gray-800/40 h-full" />
            ))}
          </div>
          {/* 可拖拽锚点 */}
          {Object.entries(scene.marks).map(([key, frame]) => (
            <DraggableMark
              key={key}
              sceneId={scene.id}
              markKey={key}
              frame={frame}
              totalFrames={scene.durationInFrames}
              onMarkChange={onMarkChange}
            />
          ))}
        </div>
      </div>
    );
  }
);

SceneCard.displayName = 'SceneCard';
