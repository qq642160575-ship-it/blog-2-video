import React, { useState, useCallback } from 'react';
import { MapPin } from 'lucide-react';

interface DraggableMarkProps {
  sceneId: string;
  markKey: string;
  frame: number;
  totalFrames: number;
  onMarkChange: (sceneId: string, markKey: string, newFrame: number) => void;
}

export const DraggableMark: React.FC<DraggableMarkProps> = React.memo(
  ({ sceneId, markKey, frame, totalFrames, onMarkChange }) => {
    const [isDragging, setIsDragging] = useState(false);
    const [draftFrame, setDraftFrame] = useState<number | null>(null);
    const draftFrameRef = React.useRef<number | null>(null);

    const displayFrame = draftFrame !== null ? draftFrame : frame;
    const percentage = Math.min(100, Math.max(0, (displayFrame / totalFrames) * 100));

    const handlePointerDown = useCallback(
      (e: React.PointerEvent) => {
        e.preventDefault();
        e.stopPropagation();
        setIsDragging(true);
        setDraftFrame(frame);
        draftFrameRef.current = frame;

        const track = (e.currentTarget as HTMLElement).closest('.rhythm-track') as HTMLDivElement;
        let rafId: number | null = null;

        const onPointerMove = (moveEvent: PointerEvent) => {
          if (!track || rafId !== null) return;
          rafId = requestAnimationFrame(() => {
            rafId = null;
            const rect = track.getBoundingClientRect();
            let newX = moveEvent.clientX - rect.left;
            newX = Math.max(0, Math.min(newX, rect.width));
            const newFrame = Math.round((newX / rect.width) * totalFrames);
            setDraftFrame(newFrame);
            draftFrameRef.current = newFrame;
          });
        };

        const onPointerUp = () => {
          setIsDragging(false);
          if (rafId !== null) {
            cancelAnimationFrame(rafId);
            rafId = null;
          }
          if (draftFrameRef.current !== null) {
            onMarkChange(sceneId, markKey, draftFrameRef.current);
          }
          setDraftFrame(null);
          draftFrameRef.current = null;
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
          paddingLeft: '18px',
          paddingRight: '18px',
          marginLeft: '-18px',
        }}
        onPointerDown={handlePointerDown}
      >
        <div
          className={`w-0.5 h-full transition-colors ${
            isDragging ? 'bg-blue-400' : 'bg-blue-500/70 group-hover/mark:bg-blue-400'
          }`}
        />
        <div className="absolute -top-1 pointer-events-none">
          <MapPin
            className={`w-4 h-4 transition-all ${
              isDragging
                ? 'text-blue-200 fill-blue-500 scale-125'
                : 'text-blue-400 fill-blue-900 group-hover/mark:scale-110 group-hover/mark:text-blue-300'
            }`}
          />
        </div>
        <span
          className={`absolute bottom-full mb-1 left-1/2 -translate-x-1/2 text-[10px] font-mono whitespace-nowrap pointer-events-none transition-all ${
            isDragging
              ? 'text-blue-100 bg-blue-700 px-1.5 py-0.5 rounded opacity-100 shadow-lg'
              : 'text-blue-400 opacity-60 group-hover/mark:opacity-100 group-hover/mark:text-blue-200 group-hover/mark:bg-blue-900/80 group-hover/mark:px-1.5 group-hover/mark:py-0.5 group-hover/mark:rounded'
          }`}
        >
          {markKey} {(displayFrame / 30).toFixed(1)}s
        </span>
      </div>
    );
  }
);

DraggableMark.displayName = 'DraggableMark';
