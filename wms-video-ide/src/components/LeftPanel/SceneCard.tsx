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

export const SceneCard: React.FC<SceneCardProps> = React.memo(
  ({ scene, isActive, onSelect, onDurationChange, onMarkChange }) => {
    const estimatedSec = scene.script.replace(/\s/g, '').length / 4;
    const isTooLong = estimatedSec > scene.durationInFrames / 30;

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
        {isActive && <div className="absolute left-0 top-0 bottom-0 w-0.5 bg-purple-500" />}

        <div className="px-3 pt-3 pb-2">
          <div className="flex justify-between items-center mb-2">
            <div
              className="flex items-center gap-1.5 bg-gray-900 rounded px-2 py-1.5 border border-gray-700 min-h-[36px]"
              onClick={(e) => e.stopPropagation()}
            >
              <Clock className="w-3.5 h-3.5 text-gray-400" />
              <input
                type="number"
                value={scene.durationInFrames / 30}
                onChange={handleDurationChange}
                className="w-10 bg-transparent text-[12px] text-center text-gray-300 outline-none font-mono"
              />
              <span className="text-[11px] text-gray-500">s</span>
            </div>
            <div className="flex items-center gap-2">
              {isTooLong && (
                <span className="text-[11px] text-red-400 font-mono" title="文案时长超出片段时长">
                  超长
                </span>
              )}
              <span
                className={`text-[11px] px-2 py-1 rounded ${
                  isActive
                    ? 'text-purple-300 bg-purple-500/20'
                    : 'text-gray-400 bg-gray-800'
                }`}
              >
                {scene.componentType}
              </span>
            </div>
          </div>

          <p
            className={`text-[12px] leading-relaxed truncate ${
              isActive ? 'text-purple-200' : 'text-gray-400'
            }`}
            title={scene.script}
          >
            {scene.script}
          </p>
        </div>

        <div className="h-10 bg-black/40 border-t border-gray-800/50 relative rhythm-track">
          <div className="absolute inset-0 flex pointer-events-none">
            {Array.from({
              length: Math.max(1, Math.floor(scene.durationInFrames / 30)),
            }).map((_, i) => (
              <div key={i} className="flex-1 border-r border-gray-800/40 h-full relative">
                <span className="absolute left-1 top-1 text-[9px] text-gray-600 font-mono leading-none">
                  {i}s
                </span>
              </div>
            ))}
          </div>
          {Object.keys(scene.marks).length === 0 && (
            <span className="absolute right-2 top-1 text-[10px] text-gray-700 font-mono leading-none pointer-events-none">
              暂无时间锚点
            </span>
          )}
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
