import React, { useState, useCallback } from 'react';
import { MapPin } from 'lucide-react';

interface DraggableMarkProps {
  sceneId: string;
  markKey: string;
  frame: number;
  totalFrames: number;
  onMarkChange: (sceneId: string, markKey: string, newFrame: number) => void;
}

/**
 * 可拖拽锚点组件。
 *
 * 修正点：
 * 1. 从 App.tsx 独立出来，不再内联定义
 * 2. 本地 draftFrame 在拖拽期间先行更新，pointerup 时才提交 store → 消除拖拽期间的 store 风暴
 * 3. pointermove 用 requestAnimationFrame 节流，防止 60fps 高频触发
 */
export const DraggableMark: React.FC<DraggableMarkProps> = React.memo(
  ({ sceneId, markKey, frame, totalFrames, onMarkChange }) => {
    const [isDragging, setIsDragging] = useState(false);
    // 拖拽期间的本地帧值，不直接写 store
    const [draftFrame, setDraftFrame] = useState<number | null>(null);

    const displayFrame = draftFrame !== null ? draftFrame : frame;
    const percentage = Math.min(100, Math.max(0, (displayFrame / totalFrames) * 100));

    const handlePointerDown = useCallback(
      (e: React.PointerEvent) => {
        e.preventDefault();
        e.stopPropagation();
        setIsDragging(true);
        setDraftFrame(frame);

        const track = (e.currentTarget as HTMLElement).closest(
          '.rhythm-track'
        ) as HTMLDivElement;

        let rafId: number | null = null;

        const onPointerMove = (moveEvent: PointerEvent) => {
          if (!track) return;
          // RAF 节流：跳过本帧已有的调度
          if (rafId !== null) return;
          rafId = requestAnimationFrame(() => {
            rafId = null;
            const rect = track.getBoundingClientRect();
            let newX = moveEvent.clientX - rect.left;
            newX = Math.max(0, Math.min(newX, rect.width));
            const newFrame = Math.round((newX / rect.width) * totalFrames);
            // 仅更新本地 draft，不触发 store
            setDraftFrame(newFrame);
          });
        };

        const onPointerUp = () => {
          setIsDragging(false);
          if (rafId !== null) {
            cancelAnimationFrame(rafId);
            rafId = null;
          }
          // pointerup 时才提交最终值到 store
          setDraftFrame((latest) => {
            if (latest !== null) {
              onMarkChange(sceneId, markKey, latest);
            }
            return null;
          });
          window.removeEventListener('pointermove', onPointerMove);
          window.removeEventListener('pointerup', onPointerUp);
        };

        window.addEventListener('pointermove', onPointerMove);
        window.addEventListener('pointerup', onPointerUp);
      },
      [frame, totalFrames, sceneId, markKey, onMarkChange]
    );

    return (
      <div
        className="absolute top-0 bottom-0 flex flex-col items-center group/mark"
        style={{
          left: `${percentage}%`,
          transform: 'translateX(-50%)',
          zIndex: isDragging ? 50 : 10,
          cursor: 'ew-resize',
        }}
        onPointerDown={handlePointerDown}
      >
        <div
          className={`w-1 h-full transition-colors ${
            isDragging ? 'bg-blue-400' : 'bg-blue-500/60 group-hover/mark:bg-blue-400'
          }`}
        />
        <div className="absolute -top-1 pointer-events-none">
          <MapPin
            className={`w-3.5 h-3.5 transition-all ${
              isDragging
                ? 'text-blue-200 fill-blue-500 scale-125'
                : 'text-blue-400 fill-blue-900'
            }`}
          />
        </div>
        <span
          className={`absolute bottom-full mb-1 left-1/2 -translate-x-1/2 text-[9px] font-mono text-blue-200 bg-blue-900 px-1.5 py-0.5 rounded whitespace-nowrap pointer-events-none transition-opacity ${
            isDragging ? 'opacity-100' : 'opacity-0 group-hover/mark:opacity-100'
          }`}
        >
          {markKey} {(displayFrame / 30).toFixed(1)}s
        </span>
      </div>
    );
  }
);

DraggableMark.displayName = 'DraggableMark';
