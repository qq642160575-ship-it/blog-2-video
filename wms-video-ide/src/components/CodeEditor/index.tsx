import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import Editor from '@monaco-editor/react';
import type * as Monaco from 'monaco-editor';
import {
  AlertTriangle,
  ChevronDown,
  ChevronRight,
  History,
  ListTodo,
  RefreshCw,
  RotateCcw,
  TerminalSquare,
} from 'lucide-react';
import { useIdeStore } from '../../store/useIdeStore';
import { selectActiveScene } from '../../store/selectors';
import type { ArtifactTab } from '../../store/useIdeStore';
import { ArtifactViewer } from '../ArtifactViewer';
import { ValidationPanel } from '../ValidationPanel';
import type { WorkflowHistoryItem, WorkflowName } from '../../types/workflow';
import {
  formatWorkflowAction,
  getNodePresentation,
  getWorkflowLabel,
} from '../../utils/workflowUi';

type PanelTab = 'progress' | 'history' | 'logs';

const panelTabLabel: Record<PanelTab, string> = {
  progress: '当前进度',
  history: '历史检查点',
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
  const rewriteStatus = useIdeStore((s) => s.rewriteStatus);
  const aiStatus = useIdeStore((s) => s.aiStatus);
  const sourceText = useIdeStore((s) => s.sourceText);
  const oralScript = useIdeStore((s) => s.oralScript);
  const setRewriteStatus = useIdeStore((s) => s.setRewriteStatus);
  const setAiStatus = useIdeStore((s) => s.setAiStatus);
  const addProcessLog = useIdeStore((s) => s.addProcessLog);
  const clearProcessLogs = useIdeStore((s) => s.clearProcessLogs);
  const setProcessStartTime = useIdeStore((s) => s.setProcessStartTime);
  const setOralScript = useIdeStore((s) => s.setOralScript);
  const setScenes = useIdeStore((s) => s.setScenes);
  const scriptThreadId = useIdeStore((s) => s.scriptThreadId);
  const scriptCheckpointId = useIdeStore((s) => s.scriptCheckpointId);
  const animationThreadId = useIdeStore((s) => s.animationThreadId);
  const animationCheckpointId = useIdeStore((s) => s.animationCheckpointId);
  const setScriptThreadContext = useIdeStore((s) => s.setScriptThreadContext);
  const setAnimationThreadContext = useIdeStore((s) => s.setAnimationThreadContext);
  const historyWorkflow = useIdeStore((s) => s.historyWorkflow);
  const historyItemsByWorkflow = useIdeStore((s) => s.historyItemsByWorkflow);
  const historyLoadingByWorkflow = useIdeStore((s) => s.historyLoadingByWorkflow);
  const workflowProgressByName = useIdeStore((s) => s.workflowProgressByName);
  const setHistoryItems = useIdeStore((s) => s.setHistoryItems);
  const setHistoryWorkflow = useIdeStore((s) => s.setHistoryWorkflow);
  const setWorkflowProgress = useIdeStore((s) => s.setWorkflowProgress);
  const applyArtifacts = useIdeStore((s) => s.updateArtifacts);
  const resetWorkflowProgress = useIdeStore((s) => s.resetWorkflowProgress);
  const loadHistory = useIdeStore((s) => s.loadHistory);
  const scriptBaseline = useIdeStore((s) => s.scriptBaseline);
  const animationBaseline = useIdeStore((s) => s.animationBaseline);
  const captureScriptBaseline = useIdeStore((s) => s.captureScriptBaseline);
  const captureAnimationBaseline = useIdeStore((s) => s.captureAnimationBaseline);

  const activeTab = useIdeStore((s) => s.activeTab);
  const setActiveTab = useIdeStore((s) => s.setActiveTab);
  const [panelTab, setPanelTab] = useState<PanelTab>('progress');
  const [elapsedMs, setElapsedMs] = useState(0);
  const [statusPanelHeight, setStatusPanelHeight] = useState(368);
  const [isResizingStatusPanel, setIsResizingStatusPanel] = useState(false);
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

  const selectedWorkflow = historyWorkflow ?? availableWorkflows[0] ?? null;
  const historyItems = selectedWorkflow ? historyItemsByWorkflow[selectedWorkflow] ?? [] : [];
  const historyLoading = selectedWorkflow
    ? historyLoadingByWorkflow[selectedWorkflow]
    : false;
  const currentCheckpointId =
    selectedWorkflow === 'conversational_tone' ? scriptCheckpointId : animationCheckpointId;
  const selectedProgress = selectedWorkflow
    ? workflowProgressByName[selectedWorkflow]
    : null;

  const hasScriptDraftChanges =
    !!scriptBaseline &&
    (scriptBaseline.sourceText !== sourceText || scriptBaseline.oralScript !== oralScript);
  const hasAnimationDraftChanges = animationBaseline !== JSON.stringify(scenes);

  const rollbackRiskMessage = useMemo(() => {
    if (selectedWorkflow === 'conversational_tone' && hasScriptDraftChanges) {
      return '你当前改过原文或口播稿，恢复后这些草稿可能与历史检查点不一致。';
    }

    if (selectedWorkflow === 'animation' && hasAnimationDraftChanges) {
      return '你当前改过镜头脚本、代码或时间轴，恢复后这些本地修改可能被新的结果覆盖。';
    }

    return '从历史检查点恢复时，系统会继续向下执行后续节点，而不是只查看旧结果。';
  }, [hasAnimationDraftChanges, hasScriptDraftChanges, selectedWorkflow]);

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
    if (aiStatus === 'idle' && animationThreadId) {
      void loadHistory('animation');
    }
  }, [aiStatus, animationThreadId, loadHistory]);

  useEffect(() => {
    if (rewriteStatus === 'success' && scriptThreadId) {
      void loadHistory('conversational_tone');
    }
  }, [loadHistory, rewriteStatus, scriptThreadId]);

  useEffect(() => {
    logsEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [processLogs, panelTab]);

  useEffect(() => {
    if (!selectedWorkflow && availableWorkflows.length > 0) {
      setHistoryWorkflow(availableWorkflows[0]);
    }
  }, [availableWorkflows, selectedWorkflow, setHistoryWorkflow]);

  const readSse = useCallback(
    async (response: Response, workflow: WorkflowName, onUpdate?: (payload: any) => void) => {
      const reader = response.body?.getReader();
      const decoder = new TextDecoder('utf-8');

      if (!reader) {
        throw new Error('无法初始化流式读取器');
      }

      let buffer = '';

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() || '';

        for (const line of lines) {
          if (!line.startsWith('data: ')) continue;
          const dataStr = line.replace('data: ', '').trim();
          if (!dataStr) continue;

          let payload;
          try {
            payload = JSON.parse(dataStr);
          } catch (error) {
            console.warn('解析 SSE 数据失败:', dataStr, error);
            continue;
          }

          if (payload.thread_id) {
            if (workflow === 'conversational_tone') {
              setScriptThreadContext(payload.thread_id, payload.checkpoint_id ?? undefined);
            } else {
              setAnimationThreadContext(payload.thread_id, payload.checkpoint_id ?? undefined);
            }
          }

          if (payload.type === 'end' && payload.checkpoint_id) {
            if (workflow === 'conversational_tone') {
              setScriptThreadContext(payload.thread_id ?? scriptThreadId, payload.checkpoint_id);
            } else {
              setAnimationThreadContext(
                payload.thread_id ?? animationThreadId,
                payload.checkpoint_id
              );
            }
          }

          onUpdate?.(payload);
        }
      }
    },
    [
      animationThreadId,
      scriptThreadId,
      setAnimationThreadContext,
      setScriptThreadContext,
    ]
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

  const applyAnimationUpdate = useCallback(
    (updateData: any, logPrefix = '节点完成') => {
      const nodeName = Object.keys(updateData)[0];
      const nodeData = updateData[nodeName];
      if (!nodeName || !nodeData) return;

      addProcessLog(`${logPrefix}：${formatWorkflowAction('animation', nodeName)}`);
      markWorkflowNode('animation', nodeName, 'success');

      if (nodeName === 'parse_oral_script_node' && nodeData.parsed_script) {
        applyArtifacts({ parsedScript: nodeData.parsed_script });
      }

      if (nodeName === 'plan_scenes_node' && nodeData.scenes) {
        applyArtifacts({ scenePlan: nodeData.scenes });
      }

      if (nodeName === 'generate_marks_node' && nodeData.scenes) {
        applyArtifacts({ marks: nodeData.marks });
        const parsedScenes = nodeData.scenes.map((scene: any) => ({
          id: scene.scene_id,
          durationInFrames: scene.duration_in_frames || Math.ceil(((scene.end || 30) - (scene.start || 0))),
          componentType: scene.scene_id.replace(/\s+/g, ''),
          script: scene.text,
          visual_design: scene.visual_goal || '',
          marks: nodeData.marks?.scene_marks?.[scene.scene_id] || {},
          code: '// Waiting for regenerated scene code.',
        }));
        setScenes(parsedScenes);
        addProcessLog(`已生成 ${parsedScenes.length} 个镜头。`);
      }

      if (nodeName === 'compile_layout_node' && nodeData.layouts) {
        applyArtifacts({ layouts: nodeData.layouts });
      }

      if (nodeName === 'compile_motion_node' && nodeData.motions) {
        applyArtifacts({ motions: nodeData.motions });
      }

      if (nodeName === 'generate_dsl_node' && nodeData.dsl) {
        applyArtifacts({ dsl: nodeData.dsl });
      }

      if ((nodeName === 'generate_scene_code_node' || nodeName === 'repair_scene_node') && nodeData.codes) {
        applyArtifacts({ codes: nodeData.codes });
        Object.values(nodeData.codes).forEach((coder: any) => {
          updateSceneCode(coder.scene_id, coder.code);
          addProcessLog(`代码已更新：${coder.scene_id}`);
        });
      }

      if (nodeData.validations) {
        applyArtifacts({ validations: nodeData.validations });
      }
    },
    [addProcessLog, applyArtifacts, markWorkflowNode, setScenes, updateSceneCode]
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

  const buildRestoreConfirmText = useCallback(
    (workflow: WorkflowName, item: WorkflowHistoryItem) => {
      const createdAt = item.created_at
        ? new Date(item.created_at).toLocaleString('zh-CN', { hour12: false })
        : '未知时间';
      const actionLabel = formatWorkflowAction(
        workflow,
        (item.values?.last_action as string | undefined) ?? null
      );
      const nextNodes =
        item.next_nodes.length > 0
          ? item.next_nodes.map((node) => formatWorkflowAction(workflow, node)).join('、')
          : '无';

      const lines = [
        `将恢复到 ${createdAt} 的检查点。`,
        `影响范围：${getWorkflowLabel(workflow)}`,
        `当时阶段：${actionLabel}`,
        `恢复后会继续重新生成：${nextNodes}`,
      ];

      if (workflow === 'conversational_tone' && hasScriptDraftChanges) {
        lines.push('警告：你当前修改过原文或口播稿，这些草稿可能被新的结果覆盖。');
      }

      if (workflow === 'animation' && hasAnimationDraftChanges) {
        lines.push('警告：你当前修改过镜头脚本、代码或时间轴，这些本地修改可能被新的结果覆盖。');
      }

      lines.push('是否继续“恢复到此并重新生成”？');
      return lines.join('\n');
    },
    [hasAnimationDraftChanges, hasScriptDraftChanges]
  );

  const forkFromCheckpoint = useCallback(
    async (workflow: WorkflowName, item: WorkflowHistoryItem) => {
      const threadId = workflow === 'conversational_tone' ? scriptThreadId : animationThreadId;
      if (!threadId) return;

      const confirmed = window.confirm(buildRestoreConfirmText(workflow, item));
      if (!confirmed) return;

      setProcessStartTime(Date.now());
      setPanelTab('progress');
      const workflowLabel = getWorkflowLabel(workflow);
      setWorkflowProgress(workflow, {
        status: 'running',
        nodeKey: item.next_nodes[0] ?? null,
        nodeLabel: `正在恢复${workflowLabel}`,
        description: `系统会先回到这个检查点，再重新生成后续 ${item.next_nodes.length} 个节点。`,
        lastError: null,
      });

      if (workflow === 'conversational_tone') {
        setRewriteStatus('generating');
        setAiStatus('idle');
      } else {
        setAiStatus('generating');
        setRewriteStatus('idle');
      }

      addProcessLog(`开始从历史检查点恢复：${item.checkpoint_id.slice(0, 12)}`);

      try {
        const response = await fetch(`/api/workflows/${workflow}/fork_sse`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            thread_id: threadId,
            checkpoint_id: item.checkpoint_id,
            values: null,
            as_node: null,
          }),
        });

        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`);
        }

        await readSse(response, workflow, (payload) => {
          if (payload.type === 'error') {
            throw new Error(payload.message || '恢复并重新生成失败');
          }

          if (payload.type === 'end') {
            if (payload.status === 'error') {
              throw new Error(payload.progress?.description || '恢复并重新生成失败');
            }
            return;
          }

          if (payload.type === 'setup') {
            setWorkflowProgress(workflow, {
              status: 'running',
              nodeLabel: `正在恢复${getWorkflowLabel(workflow)}`,
              description: '已连接到恢复任务，系统正在准备重新生成。',
              lastError: null,
            });
            return;
          }

          if (payload.type === 'updates' && payload.data) {
            let updateData = payload.data;
            if (updateData.type === 'updates' && updateData.data) {
              updateData = updateData.data;
            }

            if (workflow === 'conversational_tone') {
              const nodeName = Object.keys(updateData)[0];
              const nodeData = updateData[nodeName];
              if (!nodeName || !nodeData) return;

              addProcessLog(`恢复后完成阶段：${formatWorkflowAction(workflow, nodeName)}`);
              markWorkflowNode(workflow, nodeName, 'success');

              if (nodeData.current_script) {
                setOralScript(nodeData.current_script);
              }

              if (nodeName === 'finalize_oral_script_node' && nodeData.oral_script_result?.oral_script) {
                setOralScript(nodeData.oral_script_result.oral_script);
                applyArtifacts({
                  parsedScript: {
                    source_id: 'oral-script',
                    intent: 'oral_script',
                    tone: nodeData.oral_script_result.script_metadata?.tone || 'conversational',
                    emotion_curve: [],
                    segments: nodeData.oral_script_result.script_segments || [],
                  },
                });
              }
            } else {
              applyAnimationUpdate(updateData, '恢复后完成阶段');
            }
          }
        });

        addProcessLog('已恢复到指定检查点，并完成后续重新生成。');
        setWorkflowProgress(workflow, {
          status: 'success',
          description: '恢复成功，当前结果已经刷新为新的执行结果。',
          lastError: null,
        });
        if (workflow === 'conversational_tone') {
          setRewriteStatus('success');
          captureScriptBaseline();
        } else {
          setAiStatus('idle');
          captureAnimationBaseline();
        }
        await loadHistory(workflow);
      } catch (error) {
        const message = (error as Error).message;
        addProcessLog(`恢复失败：${message}`);
        setWorkflowProgress(workflow, {
          status: 'error',
          description: '恢复任务中断，请先刷新检查点或重试当前步骤。',
          lastError: message,
        });
        if (workflow === 'conversational_tone') {
          setRewriteStatus('error');
        } else {
          setAiStatus('error');
        }
      } finally {
        setProcessStartTime(null);
      }
    },
    [
      animationThreadId,
      applyAnimationUpdate,
      buildRestoreConfirmText,
      captureAnimationBaseline,
      captureScriptBaseline,
      loadHistory,
      markWorkflowNode,
      readSse,
      scriptThreadId,
      setAiStatus,
      setOralScript,
      setProcessStartTime,
      setRewriteStatus,
      setWorkflowProgress,
      addProcessLog,
    ]
  );

  const retryRewrite = useCallback(async () => {
    setRewriteStatus('generating');
    setAiStatus('idle');
    setPanelTab('progress');
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
      const response = await fetch('/api/generate_script_sse', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ source_text: sourceText, thread_id: scriptThreadId }),
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      await readSse(response, 'conversational_tone', (payload) => {
        if (payload.type === 'error') {
          throw new Error(payload.message || '口播稿重试失败');
        }

        if (payload.type === 'end') {
          if (payload.status === 'error') {
            throw new Error(payload.progress?.description || '口播稿重试失败');
          }
          return;
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

          if (nodeName === 'finalize_oral_script_node' && nodeData.oral_script_result?.oral_script) {
            setOralScript(nodeData.oral_script_result.oral_script);
            applyArtifacts({
              parsedScript: {
                source_id: 'oral-script',
                intent: 'oral_script',
                tone: nodeData.oral_script_result.script_metadata?.tone || 'conversational',
                emotion_curve: [],
                segments: nodeData.oral_script_result.script_segments || [],
              },
            });
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
    readSse,
    scriptThreadId,
    setAiStatus,
    setOralScript,
    setProcessStartTime,
    setRewriteStatus,
    setWorkflowProgress,
    sourceText,
  ]);

  const retryVideo = useCallback(async () => {
    setAiStatus('generating');
    setRewriteStatus('idle');
    setPanelTab('progress');
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
      const response = await fetch('/api/generate_animation_sse', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ oral_script: oralScript, thread_id: animationThreadId }),
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

        await readSse(response, 'animation', (payload) => {
          if (payload.type === 'error') {
            throw new Error(payload.message || '分镜重试失败');
          }

        if (payload.type === 'end') {
          if (payload.status === 'error') {
            throw new Error(payload.progress?.description || '分镜重试失败');
          }
          return;
        }

        if (payload.type === 'setup') {
          setWorkflowProgress('animation', {
            status: 'running',
            nodeLabel: '正在重试分镜生成',
            description: '已连接到分镜重试任务。',
          });
          return;
        }

        if (payload.type === 'updates' && payload.data) {
          let updateData = payload.data;
          if (updateData.type === 'updates' && updateData.data) {
            updateData = updateData.data;
          }

          applyAnimationUpdate(updateData);
        }
        });

      addProcessLog('分镜与代码重试完成。');
      setWorkflowProgress('animation', {
        status: 'success',
        description: '分镜与代码已重新生成完成。',
      });
      setAiStatus('idle');
      captureAnimationBaseline();
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
    animationThreadId,
    applyAnimationUpdate,
    captureAnimationBaseline,
    oralScript,
    readSse,
    setAiStatus,
    setProcessStartTime,
    setRewriteStatus,
    setWorkflowProgress,
  ]);

  const retryHandler = useMemo(() => {
    if (lastErrorType === 'rewrite') return retryRewrite;
    if (lastErrorType === 'video') return retryVideo;
    return undefined;
  }, [lastErrorType, retryRewrite, retryVideo]);

  return (
    <div className="flex w-[42%] flex-col bg-[#1e1e1e]">
      <div className="flex flex-shrink-0 items-center border-b border-gray-800 bg-[#18181b] px-2 py-2">
        <div className="flex flex-wrap gap-1">
          {(['code', 'validation', 'layout', 'motion', 'dsl', 'marks', 'scenes', 'script'] as ArtifactTab[]).map(
            (tab) => (
              <button
                key={tab}
                onClick={() => setActiveTab(tab)}
                className={`rounded px-3 py-1.5 text-[11px] font-medium transition-colors ${
                  activeTab === tab
                    ? 'bg-blue-500/10 text-blue-400 border border-blue-500/20'
                    : 'text-gray-400 hover:bg-gray-800 hover:text-gray-200'
                }`}
              >
                {tab.toUpperCase()}
              </button>
            )
          )}
        </div>
      </div>

      <div className="min-h-0 flex-1 border-b border-gray-800">
        {!hasScenes ? (
          <div className="flex h-full items-center justify-center bg-[#111113] px-6">
            <div className="max-w-[260px] text-center">
              <p className="text-sm text-gray-300">完成步骤 2 后，这里会显示编译产物。</p>
            </div>
          </div>
        ) : (
          <div className="h-full">
            {activeTab === 'code' && (
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
            )}
            {activeTab === 'validation' && <ValidationPanel />}
            {activeTab === 'layout' && <ArtifactViewer label="Layout" artifact={useIdeStore.getState().layouts[activeSceneId]} />}
            {activeTab === 'motion' && <ArtifactViewer label="Motion" artifact={useIdeStore.getState().motions[activeSceneId]} />}
            {activeTab === 'dsl' && <ArtifactViewer label="DSL" artifact={useIdeStore.getState().dsl[activeSceneId]} />}
            {activeTab === 'marks' && <ArtifactViewer label="Marks" artifact={useIdeStore.getState().marks} />}
            {activeTab === 'scenes' && <ArtifactViewer label="Scenes" artifact={useIdeStore.getState().scenePlan} />}
            {activeTab === 'script' && <ArtifactViewer label="Script" artifact={useIdeStore.getState().parsedScript} />}
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
                availableWorkflows.forEach((workflow) => {
                  setHistoryItems(workflow, []);
                  resetWorkflowProgress(workflow);
                });
              }}
              className="min-h-10 rounded border border-gray-700 px-3 py-2 text-[11px] text-gray-400 transition-colors hover:text-white"
            >
              清空日志
            </button>
            <button
              onClick={() => {
                availableWorkflows.forEach((workflow) => {
                  void loadHistory(workflow);
                });
              }}
              disabled={
                availableWorkflows.length === 0 ||
                availableWorkflows.some((workflow) => historyLoadingByWorkflow[workflow])
              }
              className="flex min-h-10 items-center gap-1 rounded border border-violet-500/30 px-3 py-2 text-[11px] text-violet-300 transition-colors hover:bg-violet-500/10 disabled:opacity-50"
            >
              <RefreshCw
                className={`h-3 w-3 ${
                  availableWorkflows.some((workflow) => historyLoadingByWorkflow[workflow])
                    ? 'animate-spin'
                    : ''
                }`}
              />
              刷新检查点
            </button>
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
                  onClick={() => setPanelTab(tab)}
                  className={`flex min-h-10 items-center gap-1 rounded border px-3 py-2 text-[11px] transition-colors ${
                    panelTab === tab
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
          {panelTab === 'progress' && selectedWorkflow && selectedProgress && (
            <div className="space-y-3">
              {availableWorkflows.length > 1 && (
                <div className="flex gap-2">
                  {availableWorkflows.map((workflow) => (
                    <button
                      key={workflow}
                      onClick={() => setHistoryWorkflow(workflow)}
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
                  <p>从历史检查点恢复时，系统会继续向下执行，而不是只打开旧结果。</p>
                </div>
              </div>
            </div>
          )}

          {panelTab === 'history' && (
            <div className="space-y-3">
              {availableWorkflows.length > 1 && (
                <div className="flex gap-2">
                  {availableWorkflows.map((workflow) => (
                    <button
                      key={workflow}
                      onClick={() => setHistoryWorkflow(workflow)}
                      className={`rounded border px-3 py-2 text-[11px] transition-colors ${
                        selectedWorkflow === workflow
                          ? 'border-violet-500/40 bg-violet-500/10 text-violet-300'
                          : 'border-gray-800 text-gray-500 hover:text-gray-300'
                      }`}
                    >
                      {getWorkflowLabel(workflow)}
                    </button>
                  ))}
                </div>
              )}

              {selectedWorkflow && (
                <div className="rounded-lg border border-orange-500/20 bg-orange-500/10 px-3 py-3 text-[12px] leading-relaxed text-orange-100">
                  <div className="flex items-start gap-2">
                    <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
                    <div>
                      <p className="font-medium">恢复说明</p>
                      <p className="mt-1 text-orange-200/90">{rollbackRiskMessage}</p>
                    </div>
                  </div>
                </div>
              )}

              {!selectedWorkflow && (
                <div className="rounded border border-dashed border-gray-800 px-3 py-4 text-[12px] text-gray-500">
                  还没有可查看的检查点。先完成一次生成，这里才会出现可恢复的历史阶段。
                </div>
              )}

              {selectedWorkflow && historyItems.length === 0 && !historyLoading && (
                <div className="rounded border border-dashed border-gray-800 px-3 py-4 text-[12px] text-gray-500">
                  当前流程还没有形成可恢复的阶段结果。至少完成 1 个节点后，才能从检查点重新开始。
                </div>
              )}

              {historyItems.map((item) => {
                const actionLabel = formatWorkflowAction(
                  selectedWorkflow as WorkflowName,
                  (item.values?.last_action as string | undefined) ?? null
                );
                const createdAt = item.created_at
                  ? new Date(item.created_at).toLocaleString('zh-CN', { hour12: false })
                  : '未知时间';
                const nextNodes =
                  item.next_nodes.length > 0
                    ? item.next_nodes
                        .map((node) => formatWorkflowAction(selectedWorkflow as WorkflowName, node))
                        .join('、')
                    : '无';

                return (
                  <div
                    key={item.checkpoint_id}
                    className="rounded-lg border border-violet-500/20 bg-violet-500/5 p-3"
                  >
                    <div className="flex items-start justify-between gap-3">
                      <div className="min-w-0 flex-1">
                        <div className="flex flex-wrap items-center gap-2">
                          <span className="text-[11px] text-gray-500">{createdAt}</span>
                          <span className="rounded bg-violet-500/10 px-2 py-0.5 text-[11px] text-violet-300">
                            {actionLabel}
                          </span>
                          {item.checkpoint_id === currentCheckpointId && (
                            <span className="rounded bg-emerald-500/10 px-2 py-0.5 text-[10px] text-emerald-300">
                              当前结果
                            </span>
                          )}
                        </div>
                        <p className="mt-2 text-[12px] leading-relaxed text-gray-400">
                          从这里恢复后，系统会继续重新生成后续节点，而不是只打开旧版本。
                        </p>
                        <div className="mt-2 grid gap-2 text-[11px] text-gray-500">
                          <div>后续会重新生成：{nextNodes}</div>
                          <div>检查点编号：{item.checkpoint_id.slice(0, 12)}...</div>
                        </div>
                      </div>
                      <button
                        onClick={() => forkFromCheckpoint(selectedWorkflow as WorkflowName, item)}
                        disabled={!selectedWorkflow || isGenerating}
                        className="flex min-h-11 shrink-0 items-center gap-1 rounded border border-orange-500/30 px-3 py-2 text-[11px] text-orange-300 transition-all hover:border-orange-400 hover:bg-orange-500/10 disabled:opacity-50"
                        title="恢复到这个历史阶段，并重新生成后续内容"
                      >
                        <RotateCcw className="h-3.5 w-3.5" />
                        从此处重新生成
                      </button>
                    </div>
                  </div>
                );
              })}
            </div>
          )}

          {panelTab === 'logs' && (
            <div className="space-y-2">
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
