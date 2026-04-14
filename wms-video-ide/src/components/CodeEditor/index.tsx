import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import Editor from '@monaco-editor/react';
import type * as Monaco from 'monaco-editor';
import {
  AlertTriangle,
  ChevronDown,
  ChevronRight,
  Code2,
  History,
  ListTodo,
  RefreshCw,
  RotateCcw,
  TerminalSquare,
} from 'lucide-react';
import { listBranchArtifacts } from '../../api/artifacts';
import { openGenerateScriptSse } from '../../api/compat';
import { getSessionTimeline } from '../../api/sessions';
import { cancelTask, retryTask } from '../../api/tasks';
import { useIdeStore } from '../../store/useIdeStore';
import { selectActiveScene } from '../../store/selectors';
import type { ArtifactResponse } from '../../types/artifact';
import type { TaskEventRecord } from '../../types/event';
import type { WorkflowName } from '../../types/workflow';
import { readSse } from '../../utils/sse';
import {
  formatWorkflowAction,
  getNodePresentation,
  getWorkflowLabel,
} from '../../utils/workflowUi';

type PanelTab = 'progress' | 'history' | 'logs';

const panelTabLabel: Record<PanelTab, string> = {
  progress: '当前进度',
  history: '任务历史',
  logs: '执行日志',
};

const formatElapsed = (ms: number | null) => {
  if (!ms) return '0s';
  const seconds = Math.max(0, Math.floor(ms / 1000));
  const minutes = Math.floor(seconds / 60);
  const remain = seconds % 60;
  return minutes > 0 ? `${minutes}m ${remain}s` : `${remain}s`;
};

const LogItem: React.FC<{
  log: { time: string; content: string; details?: string };
  onRetry?: () => void;
}> = ({ log, onRetry }) => {
  const [expanded, setExpanded] = useState(false);

  return (
    <div className="rounded border border-gray-800 bg-[#121216] px-3 py-2">
      <div className="flex items-start gap-2">
        <span className="shrink-0 text-[11px] text-gray-500">[{log.time}]</span>
        <div className="flex min-w-0 flex-1 items-start gap-2">
          <span className="flex-1 break-words text-[12px] leading-relaxed text-gray-300">
            {log.content}
          </span>
          {onRetry && (
            <button
              onClick={onRetry}
              className="flex min-h-9 shrink-0 items-center gap-1 rounded border border-blue-500/30 px-2 py-1 text-[11px] text-blue-300 transition-colors hover:bg-blue-500/10"
              title="重试当前失败步骤"
            >
              <RotateCcw className="h-3 w-3" />
              重试
            </button>
          )}
          {log.details && (
            <button
              onClick={() => setExpanded((value) => !value)}
              className="shrink-0 rounded p-1 text-gray-500 transition-colors hover:text-gray-300"
              title={expanded ? '收起详情' : '展开详情'}
            >
              {expanded ? (
                <ChevronDown className="h-3 w-3" />
              ) : (
                <ChevronRight className="h-3 w-3" />
              )}
            </button>
          )}
        </div>
      </div>
      {expanded && log.details && (
        <div className="mt-2 whitespace-pre-wrap break-all rounded border border-gray-800 bg-[#0d0d11] p-2 text-[11px] leading-relaxed text-gray-400">
          {log.details}
        </div>
      )}
    </div>
  );
};

export const CodeEditor: React.FC = () => {
  const activeScene = useIdeStore(selectActiveScene);
  const activeSceneId = useIdeStore((s) => s.activeSceneId);
  const scenes = useIdeStore((s) => s.scenes);
  const hasScenes = scenes.length > 0;
  const updateSceneCode = useIdeStore((s) => s.updateSceneCode);
  const processLogs = useIdeStore((s) => s.processLogs);
  const processStartTime = useIdeStore((s) => s.processStartTime);
  const currentSessionId = useIdeStore((s) => s.currentSessionId);
  const currentBranchId = useIdeStore((s) => s.currentBranchId);
  const activeAnimationTaskId = useIdeStore((s) => s.activeAnimationTaskId);
  const activeAnimationTaskStatus = useIdeStore((s) => s.activeAnimationTaskStatus);
  const taskEventsByTaskId = useIdeStore((s) => s.taskEventsByTaskId);
  const rewriteStatus = useIdeStore((s) => s.rewriteStatus);
  const aiStatus = useIdeStore((s) => s.aiStatus);
  const sourceText = useIdeStore((s) => s.sourceText);
  const setRewriteStatus = useIdeStore((s) => s.setRewriteStatus);
  const setAiStatus = useIdeStore((s) => s.setAiStatus);
  const addProcessLog = useIdeStore((s) => s.addProcessLog);
  const clearProcessLogs = useIdeStore((s) => s.clearProcessLogs);
  const setProcessStartTime = useIdeStore((s) => s.setProcessStartTime);
  const setOralScript = useIdeStore((s) => s.setOralScript);
  const scriptThreadId = useIdeStore((s) => s.scriptThreadId);
  const animationThreadId = useIdeStore((s) => s.animationThreadId);
  const setScriptThreadContext = useIdeStore((s) => s.setScriptThreadContext);
  const setAnimationThreadContext = useIdeStore((s) => s.setAnimationThreadContext);
  const workflowProgressByName = useIdeStore((s) => s.workflowProgressByName);
  const setWorkflowProgress = useIdeStore((s) => s.setWorkflowProgress);
  const captureScriptBaseline = useIdeStore((s) => s.captureScriptBaseline);

  const [activeTab, setActiveTab] = useState<PanelTab>('progress');
  const [selectedWorkflow, setSelectedWorkflow] = useState<WorkflowName | null>(null);
  const [elapsedMs, setElapsedMs] = useState(0);
  const [statusPanelHeight, setStatusPanelHeight] = useState(368);
  const [isResizingStatusPanel, setIsResizingStatusPanel] = useState(false);
  const [timelineItems, setTimelineItems] = useState<TaskEventRecord[]>([]);
  const [branchArtifacts, setBranchArtifacts] = useState<ArtifactResponse[]>([]);
  const [timelineLoading, setTimelineLoading] = useState(false);
  const [artifactLoading, setArtifactLoading] = useState(false);
  const logsEndRef = useRef<HTMLDivElement>(null);

  const isGenerating = rewriteStatus === 'generating' || aiStatus === 'generating';
  const lastErrorType =
    rewriteStatus === 'error' ? 'rewrite' : aiStatus === 'error' ? 'video' : null;

  const availableWorkflows = useMemo(
    () =>
      ([
        scriptThreadId ? 'conversational_tone' : null,
        animationThreadId ? 'animation' : null,
      ].filter(Boolean) as WorkflowName[]),
    [animationThreadId, scriptThreadId]
  );
  const selectedProgress = selectedWorkflow
    ? workflowProgressByName[selectedWorkflow]
    : null;
  const activeTaskEvents = activeAnimationTaskId
    ? taskEventsByTaskId[activeAnimationTaskId] ?? []
    : [];

  useEffect(() => {
    if (!isResizingStatusPanel) return;

    const handleMouseMove = (event: MouseEvent) => {
      const nextHeight = window.innerHeight - event.clientY;
      setStatusPanelHeight(Math.min(620, Math.max(240, nextHeight)));
    };

    const handleMouseUp = () => {
      setIsResizingStatusPanel(false);
    };

    window.addEventListener('mousemove', handleMouseMove);
    window.addEventListener('mouseup', handleMouseUp);

    return () => {
      window.removeEventListener('mousemove', handleMouseMove);
      window.removeEventListener('mouseup', handleMouseUp);
    };
  }, [isResizingStatusPanel]);

  useEffect(() => {
    if (processStartTime && isGenerating) {
      setElapsedMs(Date.now() - processStartTime);
      const timer = window.setInterval(() => {
        setElapsedMs(Date.now() - processStartTime);
      }, 1000);
      return () => window.clearInterval(timer);
    }

    setElapsedMs(0);
    return undefined;
  }, [isGenerating, processStartTime]);

  useEffect(() => {
    if (!currentSessionId) {
      setTimelineItems([]);
      return;
    }
    let cancelled = false;
    setTimelineLoading(true);
    void getSessionTimeline(currentSessionId, currentBranchId, 80)
      .then((response) => {
        if (!cancelled) {
          setTimelineItems(response.items ?? []);
        }
      })
      .catch((error) => {
        console.error('load timeline error:', error);
      })
      .finally(() => {
        if (!cancelled) setTimelineLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [currentSessionId, currentBranchId, aiStatus]);

  useEffect(() => {
    if (!currentBranchId) {
      setBranchArtifacts([]);
      return;
    }
    let cancelled = false;
    setArtifactLoading(true);
    void listBranchArtifacts(currentBranchId)
      .then((response) => {
        if (!cancelled) {
          setBranchArtifacts(response.items ?? []);
        }
      })
      .catch((error) => {
        console.error('load branch artifacts error:', error);
      })
      .finally(() => {
        if (!cancelled) setArtifactLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [currentBranchId, aiStatus]);

  useEffect(() => {
    logsEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [processLogs, activeTab]);

  useEffect(() => {
    if (!selectedWorkflow && availableWorkflows.length > 0) {
      setSelectedWorkflow(availableWorkflows[0]);
    }
  }, [availableWorkflows, selectedWorkflow]);

  const readWorkflowSse = useCallback(
    async (response: Response, workflow: WorkflowName, onUpdate?: (payload: any) => void) => {
      await readSse(response, (payload) => {
        const data = payload as any;
        if (data.thread_id) {
          if (workflow === 'conversational_tone') {
            setScriptThreadContext(data.thread_id, data.checkpoint_id ?? undefined);
          } else {
            setAnimationThreadContext(data.thread_id, data.checkpoint_id ?? undefined);
          }
        }

        if (data.type === 'end' && data.checkpoint_id) {
          if (workflow === 'conversational_tone') {
            setScriptThreadContext(data.thread_id ?? scriptThreadId, data.checkpoint_id);
          } else {
            setAnimationThreadContext(data.thread_id ?? animationThreadId, data.checkpoint_id);
          }
        }

        onUpdate?.(data);
      });
    },
    [animationThreadId, scriptThreadId, setAnimationThreadContext, setScriptThreadContext]
  );

  const markWorkflowNode = useCallback(
    (workflow: WorkflowName, nodeName: string, status: 'running' | 'success', details?: string) => {
      const presentation = getNodePresentation(workflow, nodeName);
      const previous = workflowProgressByName[workflow];
      setWorkflowProgress(workflow, {
        nodeKey: nodeName,
        nodeLabel: presentation.label,
        description:
          status === 'success'
            ? `${presentation.description}${details ? ` ${details}` : ''}`
            : presentation.description,
        status,
        completedCount:
          status === 'success' ? previous.completedCount + 1 : previous.completedCount,
        lastError: null,
      });
    },
    [setWorkflowProgress, workflowProgressByName]
  );

  const handleChange = useCallback(
    (value: string | undefined) => {
      if (!activeSceneId) return;
      updateSceneCode(activeSceneId, value ?? '');
    },
    [activeSceneId, updateSceneCode]
  );

  const handleEditorMount = useCallback((_: unknown, monaco: typeof Monaco) => {
    const tsApi = monaco.languages.typescript as unknown as {
      typescriptDefaults: {
        setDiagnosticsOptions: (options: {
          noSemanticValidation: boolean;
          noSyntaxValidation: boolean;
        }) => void;
      };
      javascriptDefaults: {
        setDiagnosticsOptions: (options: {
          noSemanticValidation: boolean;
          noSyntaxValidation: boolean;
        }) => void;
      };
    };

    tsApi.typescriptDefaults.setDiagnosticsOptions({
      noSemanticValidation: true,
      noSyntaxValidation: false,
    });
    tsApi.javascriptDefaults.setDiagnosticsOptions({
      noSemanticValidation: true,
      noSyntaxValidation: false,
    });
  }, []);

  const retryRewrite = useCallback(async () => {
    setRewriteStatus('generating');
    setAiStatus('idle');
    setActiveTab('progress');
    setProcessStartTime(Date.now());
    setWorkflowProgress('conversational_tone', {
      status: 'running',
      nodeKey: null,
      nodeLabel: '正在重试口播脚本',
      description: '系统会重新生成并评估口播稿。',
      lastError: null,
    });
    addProcessLog('开始重试口播稿生成。');

    try {
      const response = await openGenerateScriptSse({
        source_text: sourceText,
        thread_id: scriptThreadId,
      });

      await readWorkflowSse(response, 'conversational_tone', (payload) => {
        if (payload.type === 'error') {
          throw new Error(payload.message || '口播稿重试失败');
        }

        if (payload.type === 'setup') {
          setWorkflowProgress('conversational_tone', {
            status: 'running',
            nodeLabel: '正在重试口播脚本',
            description: '已连接到口播稿重试任务。',
          });
          return;
        }

        if (payload.type === 'updates' && payload.data) {
          let updateData = payload.data;
          if (updateData.type === 'updates' && updateData.data) {
            updateData = updateData.data;
          }

          const nodeName = Object.keys(updateData)[0];
          const nodeData = updateData[nodeName];
          if (!nodeName || !nodeData) return;

          addProcessLog(`阶段完成：${formatWorkflowAction('conversational_tone', nodeName)}`);
          markWorkflowNode('conversational_tone', nodeName, 'success');

          if (nodeData.current_script) {
            setOralScript(nodeData.current_script);
            addProcessLog('已收到最新口播稿。', nodeData.current_script);
          }
        }
      });

      addProcessLog('口播稿重试完成。');
      setWorkflowProgress('conversational_tone', {
        status: 'success',
        description: '口播稿已重新生成完成。',
      });
      setRewriteStatus('success');
      captureScriptBaseline();
    } catch (error) {
      const message = (error as Error).message;
      addProcessLog(`口播稿重试失败：${message}`);
      setWorkflowProgress('conversational_tone', {
        status: 'error',
        description: '口播稿重试失败，请检查网络或稍后重试。',
        lastError: message,
      });
      setRewriteStatus('error');
    } finally {
      setProcessStartTime(null);
    }
  }, [
    addProcessLog,
    captureScriptBaseline,
    markWorkflowNode,
    readWorkflowSse,
    scriptThreadId,
    setAiStatus,
    setOralScript,
    setProcessStartTime,
    setRewriteStatus,
    setWorkflowProgress,
    sourceText,
  ]);

  const retryVideo = useCallback(async () => {
    if (!activeAnimationTaskId) return;
    setAiStatus('generating');
    setRewriteStatus('idle');
    setActiveTab('progress');
    setProcessStartTime(Date.now());
    setWorkflowProgress('animation', {
      status: 'running',
      nodeKey: null,
      nodeLabel: '正在重试分镜生成',
      description: '系统会重新生成镜头、视觉方案和代码。',
      lastError: null,
    });
    addProcessLog('开始重试分镜与代码生成。');

    try {
      await retryTask(activeAnimationTaskId);
      addProcessLog(`已请求重试任务：${activeAnimationTaskId}`);
      setWorkflowProgress('animation', {
        status: 'running',
        description: '已请求后端重试当前视频任务。',
      });
    } catch (error) {
      const message = (error as Error).message;
      addProcessLog(`分镜与代码重试失败：${message}`);
      setWorkflowProgress('animation', {
        status: 'error',
        description: '分镜重试失败，请检查网络或稍后重试。',
        lastError: message,
      });
      setAiStatus('error');
    } finally {
      setProcessStartTime(null);
    }
  }, [
    addProcessLog,
    activeAnimationTaskId,
    setAiStatus,
    setProcessStartTime,
    setRewriteStatus,
    setWorkflowProgress,
  ]);

  const cancelVideoTask = useCallback(async () => {
    if (!activeAnimationTaskId || !isGenerating) return;
    try {
      await cancelTask(activeAnimationTaskId);
      addProcessLog(`已请求取消任务：${activeAnimationTaskId}`);
    } catch (error) {
      addProcessLog(`取消任务失败：${(error as Error).message}`);
    }
  }, [activeAnimationTaskId, addProcessLog, isGenerating]);

  const retryHandler = useMemo(() => {
    if (lastErrorType === 'rewrite') return retryRewrite;
    if (lastErrorType === 'video') return retryVideo;
    return undefined;
  }, [lastErrorType, retryRewrite, retryVideo]);

  return (
    <div className="flex w-[42%] flex-col bg-[#1e1e1e]">
      <div className="flex flex-shrink-0 items-center justify-between border-b border-gray-800 bg-[#18181b] px-4 py-3">
        <div className="flex items-center gap-2">
          <Code2 className="h-4 w-4 text-blue-400" />
          <span className="text-xs font-semibold text-gray-300">
            {hasScenes ? 'GeneratedScene.tsx' : '代码编辑区'}
          </span>
        </div>
        <span className="text-[11px] text-gray-500">
          {hasScenes ? activeScene.componentType || '当前镜头' : '等待步骤 2 完成'}
        </span>
      </div>

      <div className="min-h-0 flex-1 border-b border-gray-800">
        {!hasScenes ? (
          <div className="flex h-full items-center justify-center bg-[#111113] px-6">
            <div className="max-w-[260px] text-center">
              <p className="text-sm text-gray-300">完成步骤 2 后，这里会显示当前镜头的代码。</p>
              <p className="mt-2 text-[12px] text-gray-500">
                只有拿到真实分镜后才开放编辑，避免示例内容干扰判断。
              </p>
            </div>
          </div>
        ) : (
          <div className="flex h-full flex-col">
            <div className="grid grid-cols-2 gap-2 border-b border-gray-800 bg-[#111113] px-3 py-2 text-[11px] text-gray-400">
              <div className="rounded border border-gray-800 bg-[#0d0d11] px-3 py-2">
                <div>Scene Artifact</div>
                <div className="mt-1 font-mono text-gray-200">
                  {activeScene.sceneArtifactId || '待生成'}
                </div>
              </div>
              <div className="rounded border border-gray-800 bg-[#0d0d11] px-3 py-2">
                <div>版本 / 状态</div>
                <div className="mt-1 font-mono text-gray-200">
                  v{activeScene.version || 1} · {activeScene.status || 'draft'}
                </div>
              </div>
              <div className="rounded border border-gray-800 bg-[#0d0d11] px-3 py-2">
                <div>脚本长度</div>
                <div className="mt-1 font-mono text-gray-200">
                  {activeScene.script.replace(/\s/g, '').length} 字
                </div>
              </div>
              <div className="rounded border border-gray-800 bg-[#0d0d11] px-3 py-2">
                <div>校验状态</div>
                <div
                  className={`mt-1 font-mono ${
                    activeScene.validationReport &&
                    (activeScene.validationReport.passed === false ||
                      Number(activeScene.validationReport.error_count ?? 0) > 0)
                      ? 'text-red-300'
                      : 'text-emerald-300'
                  }`}
                >
                  {activeScene.validationReport &&
                  (activeScene.validationReport.passed === false ||
                    Number(activeScene.validationReport.error_count ?? 0) > 0)
                    ? `失败 ${String(activeScene.validationReport.error_count ?? 1)} 项`
                    : '通过 / 待校验'}
                </div>
              </div>
            </div>

            <div className="min-h-0 flex-1">
              <Editor
                height="100%"
                defaultLanguage="typescript"
                theme="vs-dark"
                value={activeScene.code}
                onChange={handleChange}
                onMount={handleEditorMount}
                options={{
                  minimap: { enabled: false },
                  fontSize: 13,
                  fontFamily: "'JetBrains Mono', 'Fira Code', monospace",
                  wordWrap: 'on',
                  padding: { top: 16 },
                  smoothScrolling: true,
                  scrollBeyondLastLine: false,
                }}
              />
            </div>
          </div>
        )}
      </div>

      <div
        className="border-t border-gray-800 bg-[#0b0b0e]"
        onMouseDown={() => setIsResizingStatusPanel(true)}
        title="拖动调整回滚与执行状态区域高度"
      >
        <div className="mx-auto flex h-3 w-full cursor-row-resize items-center justify-center">
          <div className="h-1 w-16 rounded-full bg-gray-700 transition-colors hover:bg-gray-500" />
        </div>
      </div>

      <div
        className="flex flex-shrink-0 flex-col bg-[#0e0e11]"
        style={{ height: `${statusPanelHeight}px` }}
      >
        <div className="flex items-center justify-between gap-3 border-b border-gray-800 bg-[#18181b] px-4 py-2">
          <div className="flex items-center gap-2">
            <TerminalSquare className="h-4 w-4 text-emerald-400" />
            <span className="text-[11px] font-semibold uppercase tracking-wider text-gray-400">
              回滚与执行状态
            </span>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={() => {
                clearProcessLogs();
              }}
              className="min-h-10 rounded border border-gray-700 px-3 py-2 text-[11px] text-gray-400 transition-colors hover:text-white"
            >
              清空日志
            </button>
            <button
              onClick={() => {
                if (currentSessionId) {
                  void getSessionTimeline(currentSessionId, currentBranchId, 80).then((response) =>
                    setTimelineItems(response.items ?? [])
                  );
                }
                if (currentBranchId) {
                  void listBranchArtifacts(currentBranchId).then((response) =>
                    setBranchArtifacts(response.items ?? [])
                  );
                }
              }}
              disabled={
                (!currentSessionId && !currentBranchId) || timelineLoading || artifactLoading
              }
              className="flex min-h-10 items-center gap-1 rounded border border-violet-500/30 px-3 py-2 text-[11px] text-violet-300 transition-colors hover:bg-violet-500/10 disabled:opacity-50"
            >
              <RefreshCw
                className={`h-3 w-3 ${timelineLoading || artifactLoading ? 'animate-spin' : ''}`}
              />
              刷新数据
            </button>
            {activeAnimationTaskId && isGenerating && (
              <button
                onClick={() => void cancelVideoTask()}
                className="flex min-h-10 items-center gap-1 rounded border border-red-500/30 px-3 py-2 text-[11px] text-red-300 transition-colors hover:bg-red-500/10"
              >
                <AlertTriangle className="h-3 w-3" />
                取消任务
              </button>
            )}
          </div>
        </div>

        <div className="border-b border-gray-800 bg-[#121216] px-3 py-2">
          <div className="flex gap-2">
            {(['progress', 'history', 'logs'] as PanelTab[]).map((tab) => {
              const Icon =
                tab === 'progress' ? ListTodo : tab === 'history' ? History : TerminalSquare;
              return (
                <button
                  key={tab}
                  onClick={() => setActiveTab(tab)}
                  className={`flex min-h-10 items-center gap-1 rounded border px-3 py-2 text-[11px] transition-colors ${
                    activeTab === tab
                      ? 'border-emerald-500/40 bg-emerald-500/10 text-emerald-300'
                      : 'border-gray-800 text-gray-500 hover:text-gray-300'
                  }`}
                >
                  <Icon className="h-3.5 w-3.5" />
                  {panelTabLabel[tab]}
                </button>
              );
            })}
          </div>
        </div>

        <div className="min-h-0 flex-1 overflow-y-auto p-3 text-xs">
          {activeTab === 'progress' && selectedWorkflow && selectedProgress && (
            <div className="space-y-3">
              {availableWorkflows.length > 1 && (
                <div className="flex gap-2">
                  {availableWorkflows.map((workflow) => (
                    <button
                      key={workflow}
                      onClick={() => setSelectedWorkflow(workflow)}
                      className={`rounded border px-3 py-2 text-[11px] transition-colors ${
                        selectedWorkflow === workflow
                          ? 'border-blue-500/40 bg-blue-500/10 text-blue-300'
                          : 'border-gray-800 text-gray-500 hover:text-gray-300'
                      }`}
                    >
                      {getWorkflowLabel(workflow)}
                    </button>
                  ))}
                </div>
              )}

              <div className="rounded-lg border border-gray-800 bg-[#121216] p-4">
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <p className="text-[11px] uppercase tracking-[0.24em] text-gray-500">
                      当前处理节点
                    </p>
                    <h3 className="mt-2 text-base font-semibold text-gray-100">
                      {selectedProgress.nodeLabel}
                    </h3>
                    <p className="mt-2 text-sm leading-relaxed text-gray-400">
                      {selectedProgress.description}
                    </p>
                  </div>
                  <span
                    className={`shrink-0 rounded px-2 py-1 text-[11px] ${
                      selectedProgress.status === 'running'
                        ? 'bg-blue-500/10 text-blue-300'
                        : selectedProgress.status === 'success'
                          ? 'bg-emerald-500/10 text-emerald-300'
                          : selectedProgress.status === 'error'
                            ? 'bg-red-500/10 text-red-300'
                            : 'bg-gray-800 text-gray-400'
                    }`}
                  >
                    {selectedProgress.status === 'running'
                      ? '进行中'
                      : selectedProgress.status === 'success'
                        ? '已完成'
                        : selectedProgress.status === 'error'
                          ? '失败'
                          : '未开始'}
                  </span>
                </div>

                <div className="mt-4 grid grid-cols-3 gap-3 text-[11px] text-gray-500">
                  <div className="rounded border border-gray-800 bg-[#0d0d11] px-3 py-2">
                    <div>所属流程</div>
                    <div className="mt-1 text-sm text-gray-200">{getWorkflowLabel(selectedWorkflow)}</div>
                  </div>
                  <div className="rounded border border-gray-800 bg-[#0d0d11] px-3 py-2">
                    <div>已完成节点</div>
                    <div className="mt-1 text-sm text-gray-200">{selectedProgress.completedCount}</div>
                  </div>
                  <div className="rounded border border-gray-800 bg-[#0d0d11] px-3 py-2">
                    <div>本轮耗时</div>
                    <div className="mt-1 text-sm text-gray-200">
                      {selectedProgress.status === 'running'
                        ? formatElapsed(elapsedMs)
                        : formatElapsed(selectedProgress.updatedAt && processStartTime
                            ? selectedProgress.updatedAt - processStartTime
                            : elapsedMs)}
                    </div>
                  </div>
                </div>

                {(currentSessionId || currentBranchId || activeAnimationTaskId) && (
                  <div className="mt-4 grid gap-2 text-[11px] text-gray-500">
                    {currentSessionId && <div>Session：{currentSessionId}</div>}
                    {currentBranchId && <div>Branch：{currentBranchId}</div>}
                    {activeAnimationTaskId && (
                      <div>
                        Task：{activeAnimationTaskId}
                        {activeAnimationTaskStatus ? ` · ${activeAnimationTaskStatus}` : ''}
                      </div>
                    )}
                  </div>
                )}

                {selectedProgress.lastError && (
                  <div className="mt-4 rounded border border-red-500/20 bg-red-500/10 px-3 py-2 text-[12px] text-red-200">
                    {selectedProgress.lastError}
                  </div>
                )}
              </div>

              <div className="rounded-lg border border-gray-800 bg-[#121216] p-4">
                <p className="text-[11px] uppercase tracking-[0.24em] text-gray-500">节点说明</p>
                <div className="mt-3 space-y-2 text-[12px] leading-relaxed text-gray-400">
                  <p>脚本流程会先改写口播稿，再评估质量；达到标准后才会停止。</p>
                  <p>分镜流程会先拆分镜头，再补视觉方案，最后生成镜头代码。</p>
                  <p>当前前端已按 task、timeline 和 artifact 组织执行信息，不再提供历史回滚入口。</p>
                </div>
              </div>
            </div>
          )}

          {activeTab === 'history' && (
            <div className="space-y-3">
              <div className="rounded-lg border border-blue-500/20 bg-blue-500/10 px-3 py-3 text-[12px] leading-relaxed text-blue-100">
                <p className="font-medium">业务历史</p>
                <p className="mt-1 text-blue-200/90">
                  这里展示当前 session timeline 和 branch artifact 历史，作为现有后端能力下的主视图。
                </p>
              </div>

              <div className="rounded-lg border border-gray-800 bg-[#121216] p-3">
                <div className="mb-3 flex items-center justify-between gap-3">
                  <p className="text-[11px] uppercase tracking-[0.24em] text-gray-500">Timeline</p>
                  <span className="text-[11px] text-gray-500">
                    {timelineLoading ? '加载中…' : `${timelineItems.length} 条事件`}
                  </span>
                </div>
                <div className="space-y-2">
                  {!currentSessionId && (
                    <div className="rounded border border-dashed border-gray-800 px-3 py-4 text-[12px] text-gray-500">
                      还没有 session，上方生成视频后这里会出现任务时间线。
                    </div>
                  )}
                  {currentSessionId && timelineItems.length === 0 && !timelineLoading && (
                    <div className="rounded border border-dashed border-gray-800 px-3 py-4 text-[12px] text-gray-500">
                      当前 session 暂无时间线事件。
                    </div>
                  )}
                  {timelineItems.slice(0, 12).map((item) => (
                    <div
                      key={item.id}
                      className="rounded border border-gray-800 bg-[#0d0d11] px-3 py-2 text-[12px]"
                    >
                      <div className="flex items-center justify-between gap-3">
                        <span className="text-gray-200">{item.event_type}</span>
                        <span className="text-[11px] text-gray-500">
                          {new Date(item.created_at).toLocaleString('zh-CN', {
                            hour12: false,
                          })}
                        </span>
                      </div>
                      <div className="mt-1 text-[11px] text-gray-500">
                        {item.node_key ? `节点 ${item.node_key}` : `Task ${item.task_id}`}
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              <div className="rounded-lg border border-gray-800 bg-[#121216] p-3">
                <div className="mb-3 flex items-center justify-between gap-3">
                  <p className="text-[11px] uppercase tracking-[0.24em] text-gray-500">Artifacts</p>
                  <span className="text-[11px] text-gray-500">
                    {artifactLoading ? '加载中…' : `${branchArtifacts.length} 个产物`}
                  </span>
                </div>
                <div className="space-y-2">
                  {!currentBranchId && (
                    <div className="rounded border border-dashed border-gray-800 px-3 py-4 text-[12px] text-gray-500">
                      当前还没有 branch，上方生成视频后这里会出现当前版本产物。
                    </div>
                  )}
                  {currentBranchId && branchArtifacts.length === 0 && !artifactLoading && (
                    <div className="rounded border border-dashed border-gray-800 px-3 py-4 text-[12px] text-gray-500">
                      当前 branch 暂无 artifact。
                    </div>
                  )}
                  {branchArtifacts.slice(0, 10).map((artifact) => (
                    <div
                      key={artifact.artifact_id}
                      className="rounded border border-gray-800 bg-[#0d0d11] px-3 py-2 text-[12px]"
                    >
                      <div className="flex items-center justify-between gap-3">
                        <span className="text-gray-200">{artifact.artifact_type}</span>
                        <span className="rounded bg-gray-800 px-2 py-0.5 text-[10px] text-gray-400">
                          v{artifact.version}
                        </span>
                      </div>
                      <div className="mt-1 text-[11px] text-gray-500">
                        {artifact.summary || artifact.artifact_id}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}

          {activeTab === 'logs' && (
            <div className="space-y-2">
              {activeTaskEvents.length > 0 && (
                <div className="rounded border border-blue-500/20 bg-blue-500/10 px-3 py-2 text-[12px] text-blue-100">
                  当前视频任务已收到 {activeTaskEvents.length} 条标准事件，日志面板下方仍保留聚合后的过程日志。
                </div>
              )}
              {processLogs.length === 0 ? (
                <div className="rounded border border-dashed border-gray-800 px-3 py-4 text-[12px] text-gray-500">
                  当前还没有执行日志。开始生成、恢复或重试后，这里会展示详细过程。
                </div>
              ) : (
                processLogs.map((log, index) => {
                  const isLastRow = index === processLogs.length - 1;
                  return (
                    <LogItem
                      key={`${log.time}-${index}`}
                      log={log}
                      onRetry={isLastRow && !isGenerating ? retryHandler : undefined}
                    />
                  );
                })
              )}
              <div ref={logsEndRef} />
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
