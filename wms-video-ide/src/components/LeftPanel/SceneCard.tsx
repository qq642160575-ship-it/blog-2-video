import React, { useCallback, useMemo } from 'react';
import { AlertTriangle, CheckCircle2, Clock, Layers3, LayoutTemplate } from 'lucide-react';
import type { Scene } from '../../types/scene';
import { DraggableMark } from './DraggableMark';

interface SceneCardProps {
  index: number;
  scene: Scene;
  isActive: boolean;
  onSelect: (id: string) => void;
  onDurationChange: (id: string, frames: number) => void;
  onMarkChange: (sceneId: string, markKey: string, newFrame: number) => void;
}

export const SceneCard: React.FC<SceneCardProps> = React.memo(
  ({ index, scene, isActive, onSelect, onDurationChange, onMarkChange }) => {
    const estimatedSec = scene.script.replace(/\s/g, '').length / 4;
    const durationSec = scene.durationInFrames / 30;
    const isTooLong = estimatedSec > durationSec;
    const hasValidationError = scene.validationReport
      ? scene.validationReport.passed === false ||
        Number(scene.validationReport.error_count ?? 0) > 0 ||
        Array.isArray(scene.validationReport.failed_scenes)
      : false;
    const sceneStatus = scene.status || 'draft';
    const statusTone = useMemo(() => {
      if (sceneStatus === 'failed' || hasValidationError) {
        return 'bg-red-500/10 text-red-300 border-red-500/20';
      }
      if (sceneStatus === 'ready') {
        return 'bg-emerald-500/10 text-emerald-300 border-emerald-500/20';
      }
      return 'bg-amber-500/10 text-amber-300 border-amber-500/20';
    }, [hasValidationError, sceneStatus]);
    const sortedMarks = Object.entries(scene.marks).sort(
      (a, b) => a[1] - b[1] || a[0].localeCompare(b[0])
    );

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
        className={`relative flex cursor-pointer flex-col rounded-md border transition-all ${
          isActive
            ? 'border-violet-500/50 bg-violet-500/10'
            : 'border-gray-800 bg-[#0e0e11] hover:border-gray-700'
        }`}
      >
        {isActive && <div className="absolute bottom-0 left-0 top-0 w-0.5 bg-violet-500" />}

        <div className="px-3 pb-2 pt-3">
          <div className="mb-2 flex items-start justify-between gap-3">
            <div className="min-w-0">
              <div className="flex items-center gap-2">
                <span className="rounded bg-gray-900 px-2 py-1 text-[11px] font-mono text-gray-400">
                  #{index + 1}
                </span>
                <span
                  className={`rounded px-2 py-1 text-[11px] ${
                    isActive
                      ? 'bg-violet-500/20 text-violet-200'
                      : 'bg-gray-800 text-gray-400'
                  }`}
                >
                  {scene.componentType}
                </span>
                {isTooLong && (
                  <span className="rounded bg-red-500/10 px-2 py-1 text-[11px] font-mono text-red-400">
                    文案超长
                  </span>
                )}
                <span
                  className={`rounded border px-2 py-1 text-[11px] font-mono ${statusTone}`}
                >
                  {sceneStatus}
                </span>
              </div>
              <div className="mt-2 flex flex-wrap items-center gap-2 text-[10px] font-mono text-gray-500">
                {scene.version ? (
                  <span className="flex items-center gap-1 rounded bg-gray-900 px-2 py-1">
                    <Layers3 className="h-3 w-3" />
                    v{scene.version}
                  </span>
                ) : null}
                {scene.sceneArtifactId ? (
                  <span className="rounded bg-gray-900 px-2 py-1">
                    {scene.sceneArtifactId.slice(0, 12)}...
                  </span>
                ) : (
                  <span className="rounded bg-gray-900 px-2 py-1">待持久化</span>
                )}
                {hasValidationError ? (
                  <span className="flex items-center gap-1 rounded bg-red-500/10 px-2 py-1 text-red-300">
                    <AlertTriangle className="h-3 w-3" />
                    校验异常
                  </span>
                ) : sceneStatus === 'ready' ? (
                  <span className="flex items-center gap-1 rounded bg-emerald-500/10 px-2 py-1 text-emerald-300">
                    <CheckCircle2 className="h-3 w-3" />
                    可编辑
                  </span>
                ) : null}
                {scene.layout_spec && (
                  <span className="flex items-center gap-1 rounded bg-violet-500/10 px-2 py-1 text-violet-300 animate-pulse">
                    <LayoutTemplate className="h-3 w-3" />
                    AI 布局已就绪
                  </span>
                )}
              </div>
              <p
                className={`mt-2 line-clamp-3 break-words text-[12px] leading-relaxed ${
                  isActive ? 'text-violet-100' : 'text-gray-400'
                }`}
                title={scene.script}
              >
                {scene.script}
              </p>
              {scene.visual_design && (
                <p className="mt-2 line-clamp-2 break-words border-l-2 border-gray-700 pl-2 text-[11px] leading-relaxed text-gray-500">
                  {scene.visual_design}
                </p>
              )}
            </div>

            <label
              className="flex min-h-11 items-center gap-2 rounded border border-gray-700 bg-gray-900 px-3 py-2"
              onClick={(e) => e.stopPropagation()}
            >
              <Clock className="h-4 w-4 text-gray-400" />
              <input
                type="number"
                min={1}
                step={0.5}
                value={Math.round(durationSec * 10) / 10}
                onChange={handleDurationChange}
                className="w-14 bg-transparent text-center text-[12px] font-mono text-gray-200 outline-none"
                aria-label="镜头时长（秒）"
              />
              <span className="text-[11px] text-gray-500">秒</span>
            </label>
          </div>

          <div className="flex items-center justify-between text-[11px] font-mono text-gray-500">
            <span>预计旁白 {estimatedSec.toFixed(1)}s</span>
            <span>镜头时长 {durationSec.toFixed(1)}s</span>
          </div>
          {scene.validationReport && (
            <div
              className={`mt-2 rounded border px-2 py-1 text-[11px] ${
                hasValidationError
                  ? 'border-red-500/20 bg-red-500/10 text-red-200'
                  : 'border-emerald-500/20 bg-emerald-500/10 text-emerald-200'
              }`}
            >
              {hasValidationError
                ? `校验异常 ${String(scene.validationReport.error_count ?? 1)} 项`
                : '校验通过'}
            </div>
          )}
        </div>

        <div className="rhythm-track relative h-12 border-t border-gray-800/50 bg-black/40">
          <div className="pointer-events-none absolute inset-0 flex">
            {Array.from({
              length: Math.max(1, Math.floor(scene.durationInFrames / 30)),
            }).map((_, i) => (
              <div key={i} className="relative h-full flex-1 border-r border-gray-800/40">
                <span className="absolute left-1.5 top-1 text-[10px] font-mono leading-none text-gray-600">
                  {i}s
                </span>
              </div>
            ))}
          </div>
          {Object.keys(scene.marks).length === 0 && (
            <span className="pointer-events-none absolute right-2 top-1 text-[10px] font-mono leading-none text-gray-700">
              暂无时间锚点
            </span>
          )}
          {sortedMarks.map(([key, frame]) => (
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
