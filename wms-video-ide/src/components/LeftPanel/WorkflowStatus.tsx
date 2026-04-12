import React, { useEffect, useState } from 'react';
import { AlertCircle, CheckCircle2, Clock3, Loader2 } from 'lucide-react';
import { useIdeStore } from '../../store/useIdeStore';

const formatSeconds = (seconds: number | null | undefined): string => {
  if (seconds === null || seconds === undefined) return '估算中';
  const safeSeconds = Math.max(0, Math.round(seconds));
  if (safeSeconds < 60) return `${safeSeconds}s`;
  const minutes = Math.floor(safeSeconds / 60);
  const rest = safeSeconds % 60;
  return rest > 0 ? `${minutes}m ${rest}s` : `${minutes}m`;
};

export const WorkflowStatus: React.FC = () => {
  const rewriteStatus = useIdeStore((s) => s.rewriteStatus);
  const aiStatus = useIdeStore((s) => s.aiStatus);
  const oralScript = useIdeStore((s) => s.oralScript);
  const scenes = useIdeStore((s) => s.scenes);
  const processStartTime = useIdeStore((s) => s.processStartTime);
  const workflowProgressByName = useIdeStore((s) => s.workflowProgressByName);

  const [liveElapsed, setLiveElapsed] = useState(0);

  const activeWorkflow = aiStatus === 'generating' ? 'animation' : 'conversational_tone';
  const progress = workflowProgressByName[activeWorkflow];
  const isRunning = rewriteStatus === 'generating' || aiStatus === 'generating';

  useEffect(() => {
    if (!processStartTime || !isRunning) {
      setLiveElapsed(0);
      return;
    }

    const timer = window.setInterval(() => {
      setLiveElapsed(Math.floor((Date.now() - processStartTime) / 1000));
    }, 1000);

    return () => window.clearInterval(timer);
  }, [isRunning, processStartTime]);

  let tone = 'text-slate-300 border-slate-700 bg-slate-900/60';
  let title = '先输入原文，再生成口播稿';
  let description = '当前只需要完成第 1 步，后续区域会在准备好后自动展开。';
  let icon = <CheckCircle2 className="h-4 w-4 text-slate-400" />;
  let progressLabel = '0 / 2';
  let percent = 0;
  let detailLine: string | null = null;

  if (isRunning) {
    tone =
      activeWorkflow === 'animation'
        ? 'text-violet-100 border-violet-500/40 bg-violet-500/10'
        : 'text-blue-100 border-blue-500/40 bg-blue-500/10';
    title = progress.nodeLabel;
    description = progress.description;
    icon =
      activeWorkflow === 'animation' ? (
        <Loader2 className="h-4 w-4 animate-spin text-violet-300" />
      ) : (
        <Loader2 className="h-4 w-4 animate-spin text-blue-300" />
      );
    progressLabel = `${progress.completedCount} / ${progress.totalCount}`;
    percent = Math.max(3, Math.min(99, progress.percent));
    const elapsed = progress.elapsedSeconds || liveElapsed;
    const eta = progress.etaSeconds ?? progress.estimatedTotalSeconds;
    detailLine = `已运行 ${formatSeconds(elapsed)}，预计剩余 ${formatSeconds(eta)}`;
  } else if (rewriteStatus === 'error' || aiStatus === 'error') {
    const errorProgress = rewriteStatus === 'error'
      ? workflowProgressByName.conversational_tone
      : workflowProgressByName.animation;
    tone = 'text-red-100 border-red-500/40 bg-red-500/10';
    title = rewriteStatus === 'error' ? '口播稿生成失败' : '分镜与代码生成失败';
    description = errorProgress.lastError || errorProgress.description || '请检查日志后重试。';
    icon = <AlertCircle className="h-4 w-4 text-red-300" />;
    progressLabel = `${errorProgress.completedCount} / ${errorProgress.totalCount}`;
    percent = errorProgress.percent;
  } else if (scenes.length > 0) {
    tone = 'text-emerald-100 border-emerald-500/40 bg-emerald-500/10';
    title = '分镜、预览和代码已完成';
    description = '可以继续逐镜头微调，或基于当前版本查看历史记录。';
    icon = <CheckCircle2 className="h-4 w-4 text-emerald-300" />;
    progressLabel = '2 / 2';
    percent = 100;
  } else if (oralScript.trim()) {
    tone = 'text-amber-100 border-amber-500/40 bg-amber-500/10';
    title = '口播稿已完成';
    description = '请确认口播稿内容，然后开始生成分镜、预览和代码。';
    icon = <CheckCircle2 className="h-4 w-4 text-amber-300" />;
    progressLabel = '1 / 2';
    percent = 50;
  }

  return (
    <div className={`rounded-lg border px-4 py-3 ${tone}`}>
      <div className="flex items-start justify-between gap-3">
        <div className="flex min-w-0 items-start gap-2">
          <div className="mt-0.5">{icon}</div>
          <div className="min-w-0">
            <p className="text-sm font-semibold">{title}</p>
            <p className="mt-1 text-xs leading-relaxed opacity-80">{description}</p>
            {detailLine && (
              <p className="mt-2 flex items-center gap-1.5 text-[11px] opacity-75">
                <Clock3 className="h-3 w-3" />
                {detailLine}
              </p>
            )}
          </div>
        </div>
        <span className="rounded-full border border-white/10 px-2 py-1 text-[11px] font-mono">
          {progressLabel}
        </span>
      </div>
      <div className="mt-3 h-1.5 overflow-hidden rounded-full bg-black/30">
        <div
          className="h-full rounded-full bg-current transition-all duration-500"
          style={{ width: `${Math.max(0, Math.min(100, percent))}%` }}
        />
      </div>
    </div>
  );
};
