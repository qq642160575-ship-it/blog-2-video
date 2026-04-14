import React, { useState } from 'react';
import {
  CheckCircle2,
  ChevronDown,
  ChevronUp,
  Loader2,
  Sparkles,
  Video,
} from 'lucide-react';
import { openGenerateScriptSse } from '../../api/compat';
import { getSceneArtifact, listBranchArtifacts } from '../../api/artifacts';
import { createSession, createSessionTask } from '../../api/sessions';
import { toLogEntry, toProgressPatch } from '../../adapters/eventAdapter';
import { getCoderUpdates, toScenesFromDirectorNode } from '../../adapters/sceneAdapter';
import { useTaskSse } from '../../hooks/useTaskSse';
import { useIdeStore } from '../../store/useIdeStore';
import { readSse } from '../../utils/sse';
import { getNodePresentation } from '../../utils/workflowUi';
import type { TaskEventRecord } from '../../types/event';
import type { CompatSsePayload } from '../../adapters/workflowCompatAdapter';
import type { WorkflowName } from '../../types/workflow';

type ServerProgress = {
  status?: 'idle' | 'running' | 'success' | 'error';
  node_key?: string | null;
  node_label?: string;
  description?: string;
  completed_count?: number;
  total_count?: number;
  percent?: number;
  elapsed_seconds?: number;
  eta_seconds?: number | null;
  estimated_total_seconds?: number | null;
  detail?: Record<string, unknown>;
};

export const SourceInput: React.FC = () => {
  const streamTaskEvents = useTaskSse();
  const sourceText = useIdeStore((s) => s.sourceText);
  const setSourceText = useIdeStore((s) => s.setSourceText);
  const oralScript = useIdeStore((s) => s.oralScript);
  const setOralScript = useIdeStore((s) => s.setOralScript);
  const aiStatus = useIdeStore((s) => s.aiStatus);
  const setAiStatus = useIdeStore((s) => s.setAiStatus);
  const rewriteStatus = useIdeStore((s) => s.rewriteStatus);
  const setRewriteStatus = useIdeStore((s) => s.setRewriteStatus);
  const clearProcessLogs = useIdeStore((s) => s.clearProcessLogs);
  const addProcessLog = useIdeStore((s) => s.addProcessLog);
  const setProcessStartTime = useIdeStore((s) => s.setProcessStartTime);
  const setCurrentSessionContext = useIdeStore((s) => s.setCurrentSessionContext);
  const setActiveAnimationTask = useIdeStore((s) => s.setActiveAnimationTask);
  const setActiveAnimationTaskStatus = useIdeStore((s) => s.setActiveAnimationTaskStatus);
  const appendTaskEvent = useIdeStore((s) => s.appendTaskEvent);
  const setScenes = useIdeStore((s) => s.setScenes);
  const patchScene = useIdeStore((s) => s.patchScene);
  const updateSceneCode = useIdeStore((s) => s.updateSceneCode);
  const scriptThreadId = useIdeStore((s) => s.scriptThreadId);
  const setScriptThreadContext = useIdeStore((s) => s.setScriptThreadContext);
  const setAnimationThreadContext = useIdeStore((s) => s.setAnimationThreadContext);
  const setWorkflowProgress = useIdeStore((s) => s.setWorkflowProgress);
  const resetWorkflowProgress = useIdeStore((s) => s.resetWorkflowProgress);
  const captureScriptBaseline = useIdeStore((s) => s.captureScriptBaseline);
  const captureAnimationBaseline = useIdeStore((s) => s.captureAnimationBaseline);

  const [step1Open, setStep1Open] = useState(true);
  const [step2Open, setStep2Open] = useState(true);

  const isGeneratingVideo = aiStatus === 'generating';
  const isRewriting = rewriteStatus === 'generating';
  const sourceSummary = `${sourceText.trim().replace(/\s+/g, '').length} 字`;
  const oralSummary = oralScript.trim()
    ? `${oralScript.trim().replace(/\s+/g, '').length} 字`
    : '未生成';

  const applyServerProgress = (workflow: WorkflowName, progress?: ServerProgress) => {
    if (!progress) return;
    const fallback = getNodePresentation(workflow, progress.node_key ?? null);

    setWorkflowProgress(workflow, {
      status: progress.status ?? 'running',
      nodeKey: progress.node_key ?? null,
      nodeLabel: progress.node_label || fallback.label,
      description: progress.description || fallback.description,
      completedCount: progress.completed_count ?? 0,
      totalCount: progress.total_count ?? (workflow === 'animation' ? 3 : 2),
      percent: progress.percent ?? 0,
      elapsedSeconds: progress.elapsed_seconds ?? 0,
      etaSeconds: progress.eta_seconds ?? null,
      estimatedTotalSeconds: progress.estimated_total_seconds ?? null,
      detail: progress.detail ?? {},
      lastError: progress.status === 'error' ? progress.description ?? null : null,
    });
  };

  const applyAnimationTaskEvent = (event: TaskEventRecord) => {
    console.log('[SSE EVENT]', event.event_type, event.node_key, event.payload);
    appendTaskEvent(event);
    if (event.event_type.startsWith('task.')) {
      const nextStatus = event.event_type.replace('task.', '');
      if (
        nextStatus === 'queued' ||
        nextStatus === 'running' ||
        nextStatus === 'succeeded' ||
        nextStatus === 'failed' ||
        nextStatus === 'cancelled' ||
        nextStatus === 'retrying'
      ) {
        setActiveAnimationTaskStatus(nextStatus);
      }
    }

    const progressPatch = toProgressPatch(event, 'animation');
    if (progressPatch) {
      setWorkflowProgress(progressPatch.workflow, progressPatch.patch);
    }

    const logEntry = toLogEntry(event);
    if (logEntry) {
      addProcessLog(logEntry.content, logEntry.details);
    }

    // 新增：处理 artifact.published 事件
    if (event.event_type === 'artifact.published') {
      const payload = event.payload as any;
      const artifactType = payload.artifact_type;
      const summary = payload.summary || '';

      addProcessLog(`产物已发布：${summary}`);

      // 存储 artifact 信息到 store
      if (payload.artifact_id) {
        useIdeStore.getState().setArtifact(artifactType, {
          artifact_id: payload.artifact_id,
          artifact_type: artifactType,
          summary: summary,
          ...payload,
        } as any);
      }

      // 增强逻辑：如果产物自带数据（例如新版后端推送的分镜列表），直接更新 scenes
      if (artifactType === 'storyboard' && payload.data?.scenes) {
        const currentScenes = useIdeStore.getState().scenes;
        if (currentScenes.length === 0) {
          const parsedScenes = toScenesFromDirectorNode(payload.data.scenes);
          setScenes(parsedScenes);
          addProcessLog(`已基于发布产物加载 ${parsedScenes.length} 个分镜。`);
        }
      }
    }

    // 新增：处理 scene.layout_generated 事件
    if (event.event_type === 'scene.layout_generated') {
      const payload = event.payload as any;
      const sceneId = payload.scene_id;
      const layoutSpec = payload.layout_spec;

      if (sceneId && layoutSpec) {
        patchScene(sceneId, { layout_spec: layoutSpec });
        addProcessLog(`场景布局已同步：${sceneId}`);
      }
    }

    // 新增：处理 scene.code_generated 事件
    if (event.event_type === 'scene.code_generated') {
      const payload = event.payload as any;
      const sceneId = payload.scene_id;
      const code = payload.code;

      if (sceneId && code) {
        updateSceneCode(sceneId, code);
        useIdeStore.getState().setSceneCode(sceneId, code);
        addProcessLog(`场景代码已生成：${sceneId}`);
      }
    }

    if (event.event_type === 'workflow.node_completed') {
      const nodeData = event.payload.data as Record<string, any> | undefined;
      if (!nodeData) return;

      // 增强分镜解析：支持 nodeData.director.scenes 或直接 nodeData.scenes
      const scenesData = nodeData.director?.scenes || nodeData.scenes;

      if (event.node_key === 'director_node' && Array.isArray(scenesData)) {
        const parsedScenes = toScenesFromDirectorNode(scenesData);
        if (parsedScenes.length > 0) {
          setScenes(parsedScenes);
          addProcessLog(`已生成 ${parsedScenes.length} 个分镜。`);
          return;
        } else {
          console.warn('[SSE] Director node completed but 0 scenes parsed', nodeData);
        }
      }

      if (event.node_key === 'coder_node' && nodeData.coder) {
        getCoderUpdates(nodeData.coder).forEach((coder) => {
          if (!coder.scene_id) return;
          updateSceneCode(coder.scene_id, coder.code || '');
          addProcessLog(`代码已返回：${coder.scene_id}`);
        });
      }
    }

    if (event.event_type === 'validation.failed') {
      setWorkflowProgress('animation', {
        status: 'error',
        description: '存在校验失败的镜头，请检查日志和分镜状态。',
        lastError: '存在校验失败的镜头',
      });
      const failedScenes = event.payload.failed_scenes as string[] | undefined;
      failedScenes?.forEach((sceneId) => {
        patchScene(sceneId, {
          status: 'failed',
          validationReport: {
            passed: false,
            failedScenes,
            ...(event.payload as Record<string, unknown>),
          },
        });
      });
    }

    if (event.event_type === 'task.completed') {
      const sceneArtifactIds = event.payload.scene_artifact_ids as string[] | undefined;
      if (sceneArtifactIds?.length) {
        void Promise.all(sceneArtifactIds.map((sceneArtifactId) => getSceneArtifact(sceneArtifactId)))
          .then((sceneArtifacts) => {
            sceneArtifacts.forEach((sceneArtifact) => {
              patchScene(sceneArtifact.scene_id, {
                sceneArtifactId: sceneArtifact.scene_artifact_id,
                artifactId: sceneArtifact.artifact_id,
                version: sceneArtifact.version,
                status: sceneArtifact.status,
                validationReport: sceneArtifact.validation_report,
                previewImageUrl: sceneArtifact.preview_image_url,
                script: sceneArtifact.script_text || undefined,
                code: sceneArtifact.code_text || undefined,
                visual_design: sceneArtifact.scene_type
                  ? `${sceneArtifact.scene_type} · ${sceneArtifact.status}`
                  : undefined,
              });
            });
          })
          .catch((error) => {
            addProcessLog(`加载 scene artifact 失败：${(error as Error).message}`);
          });
      }
      setAiStatus('idle');
      captureAnimationBaseline();
      setProcessStartTime(null);
    }

    if (event.event_type === 'task.failed' || event.event_type === 'task.cancelled') {
      setAiStatus('error');
      setProcessStartTime(null);
    }
  };

  const handleRewrite = async () => {
    setRewriteStatus('generating');
    setAiStatus('idle');
    clearProcessLogs();
    resetWorkflowProgress('conversational_tone');
    setProcessStartTime(Date.now());
    setWorkflowProgress('conversational_tone', {
      status: 'running',
      nodeLabel: '正在生成口播脚本',
      description: '系统会先改写口播稿，再评估质量。',
      lastError: null,
      completedCount: 0,
    });
    addProcessLog('开始生成口播稿。');

    try {
      const response = await openGenerateScriptSse({
        source_text: sourceText,
        thread_id: scriptThreadId,
      });
      await readSse(response, (payload) => {
        const compatPayload = payload as CompatSsePayload;
        const workflowPayload = compatPayload as CompatSsePayload & { progress?: ServerProgress };
        if (compatPayload.thread_id) {
          setScriptThreadContext(
            compatPayload.thread_id,
            compatPayload.checkpoint_id ?? undefined
          );
        }

        if (workflowPayload.progress) {
          applyServerProgress('conversational_tone', workflowPayload.progress);
        }

        if (compatPayload.type === 'progress') {
          return;
        }

        if (compatPayload.type === 'setup') {
          setWorkflowProgress('conversational_tone', {
            status: 'running',
            nodeLabel: '正在生成口播脚本',
            description: '已连接到口播脚本生成任务。',
            lastError: null,
          });
          addProcessLog('已连接口播稿工作流。');
          return;
        }

        if (compatPayload.type === 'end') {
          if (compatPayload.checkpoint_id) {
            setScriptThreadContext(
              compatPayload.thread_id ?? scriptThreadId,
              compatPayload.checkpoint_id
            );
          }
          setWorkflowProgress('conversational_tone', {
            status: 'success',
            description: '口播脚本生成完成，可以继续进入分镜阶段。',
            lastError: null,
          });
          addProcessLog('口播稿工作流结束。');
          return;
        }

        if (compatPayload.type === 'error') {
          setWorkflowProgress('conversational_tone', {
            status: 'error',
            description: '口播脚本生成失败，请检查网络或稍后重试。',
            lastError: compatPayload.message || '口播脚本生成失败',
          });
          throw new Error(compatPayload.message || '口播稿生成失败');
        }

        if (compatPayload.type === 'updates' && compatPayload.data) {
          let updateData = compatPayload.data as Record<string, any>;
          if (updateData.type === 'updates' && updateData.data) {
            updateData = updateData.data as Record<string, any>;
          }

          const nodeName = Object.keys(updateData)[0];
          const nodeData = updateData[nodeName] as Record<string, any> | undefined;
          if (!nodeName || !nodeData) return;
          const presentation = getNodePresentation('conversational_tone', nodeName);
          setWorkflowProgress('conversational_tone', {
            nodeKey: nodeName,
            nodeLabel: presentation.label,
            description: presentation.description,
            status: 'running',
            lastError: null,
          });

          addProcessLog(`节点完成：${nodeName}`);

          if (nodeData.current_script) {
            setOralScript(nodeData.current_script);
            addProcessLog('已收到最新口播稿。', nodeData.current_script);
          }

          if (nodeData.review_score !== undefined) {
            addProcessLog(
              `评审得分：${nodeData.review_score}`,
              nodeData.last_feedback || undefined
            );
          }
        }
      });

      addProcessLog('口播稿生成完成。');
      setRewriteStatus('success');
      captureScriptBaseline();
      setProcessStartTime(null);
    } catch (error) {
      setWorkflowProgress('conversational_tone', {
        status: 'error',
        description: '口播脚本生成失败，请检查网络或稍后重试。',
        lastError: (error as Error).message,
      });
      console.error('口播稿生成失败:', error);
      addProcessLog(`口播稿生成失败：${(error as Error).message}`);
      setRewriteStatus('error');
      setProcessStartTime(null);
    }
  };

  const handleGenerateVideo = async () => {
    setAiStatus('generating');
    setRewriteStatus('idle');
    clearProcessLogs();
    resetWorkflowProgress('animation');
    setProcessStartTime(Date.now());
    setWorkflowProgress('animation', {
      status: 'running',
      nodeLabel: '正在生成分镜',
      description: '系统会先拆镜头，再补视觉方案，最后生成代码。',
      lastError: null,
      completedCount: 0,
    });
    addProcessLog('开始生成分镜、预览和代码。');

    try {
      const session = await createSession({
        source_type: 'text',
        source_content: oralScript,
        title: 'Animation generation',
      });
      setCurrentSessionContext(session.session_id, session.branch_id);

      const artifacts = await listBranchArtifacts(session.branch_id);
      const sourceArtifact = artifacts.items.find(
        (artifact) => artifact.artifact_type === 'source_document'
      );
      if (!sourceArtifact) {
        throw new Error('未找到 source_document artifact，无法创建视频任务');
      }

      const task = await createSessionTask(session.session_id, {
        branch_id: session.branch_id,
        task_type: 'create_video',
        request_payload: { source_artifact_id: sourceArtifact.artifact_id },
      });
      setActiveAnimationTask(task.task_id, task.status);
      setAnimationThreadContext(task.task_id, null);
      addProcessLog(`视频任务已创建：${task.task_id}`);

      await streamTaskEvents(task.task_id, {
        onEvent: applyAnimationTaskEvent,
      });
    } catch (error) {
      setWorkflowProgress('animation', {
        status: 'error',
        description: '分镜与代码生成失败，请检查日志后重试。',
        lastError: (error as Error).message,
      });
      console.error('视频生成失败:', error);
      addProcessLog(`视频生成失败：${(error as Error).message}`);
      setAiStatus('error');
      setProcessStartTime(null);
    }
  };

  return (
    <div className="flex flex-col gap-4">
      <div className="overflow-hidden rounded-lg border border-gray-800 bg-[#141416]">
        <button
          onClick={() => setStep1Open((v) => !v)}
          className="flex w-full items-center justify-between bg-[#1c1c1f] px-4 py-3 transition-colors hover:bg-[#232326]"
        >
          <div className="flex items-center gap-2">
            <span className="flex h-5 w-5 items-center justify-center rounded-full bg-blue-500/10 text-[10px] font-bold text-blue-400">
              1
            </span>
            <h3 className="text-xs font-bold tracking-wide text-gray-300">输入原文</h3>
          </div>
          <div className="flex items-center gap-3">
            {!step1Open && (
              <span className="font-mono text-[11px] text-gray-500">{sourceSummary}</span>
            )}
            {oralScript && <CheckCircle2 className="h-3.5 w-3.5 text-green-500" />}
            {step1Open ? (
              <ChevronUp className="h-4 w-4 text-gray-500" />
            ) : (
              <ChevronDown className="h-4 w-4 text-gray-500" />
            )}
          </div>
        </button>

        <div
          className={`overflow-hidden border-t border-gray-800 transition-all duration-300 ${
            step1Open ? 'max-h-[28rem] opacity-100' : 'max-h-0 opacity-0'
          }`}
        >
          <div className="relative flex flex-col gap-3 p-3">
            <textarea
              value={sourceText}
              onChange={(e) => setSourceText(e.target.value)}
              disabled={isRewriting}
              placeholder="在这里粘贴技术博客、草稿或待改写的原文。"
              className={`w-full resize-none rounded-md border border-gray-800 bg-[#0a0a0c] p-3 text-sm leading-relaxed text-gray-300 transition-all focus:border-blue-500/50 focus:outline-none ${
                isRewriting ? 'cursor-not-allowed opacity-40' : ''
              }`}
              rows={8}
            />
            {isRewriting && (
              <div className="pointer-events-auto absolute inset-3 cursor-not-allowed rounded-md bg-transparent" />
            )}
            <div className="flex items-center justify-between gap-3">
              <span className="text-[12px] text-gray-500">
                先生成口播稿，再进入分镜与代码阶段。
              </span>
              <button
                onClick={handleRewrite}
                disabled={isRewriting || !sourceText.trim()}
                className="flex items-center gap-1.5 rounded bg-blue-600 px-4 py-2.5 text-sm font-semibold text-white shadow transition-all hover:-translate-y-0.5 hover:bg-blue-500 hover:shadow-lg active:translate-y-0 disabled:opacity-50"
              >
                {isRewriting ? (
                  <Loader2 className="h-3.5 w-3.5 animate-spin" />
                ) : (
                  <Sparkles className="h-3.5 w-3.5" />
                )}
                {isRewriting ? '正在生成口播稿…' : '生成口播稿'}
              </button>
            </div>
          </div>
        </div>
      </div>

      {(oralScript.trim() || isRewriting || rewriteStatus === 'success' || aiStatus !== 'idle') && (
        <div className="overflow-hidden rounded-lg border border-gray-800 bg-[#141416]">
          <button
            onClick={() => setStep2Open((v) => !v)}
            className="flex w-full items-center justify-between bg-[#1c1c1f] px-4 py-3 transition-colors hover:bg-[#232326]"
          >
            <div className="flex items-center gap-2">
              <span className="flex h-5 w-5 items-center justify-center rounded-full bg-violet-500/10 text-[10px] font-bold text-violet-400">
                2
              </span>
              <h3 className="text-xs font-bold tracking-wide text-gray-300">确认口播稿并生成分镜</h3>
            </div>
            <div className="flex items-center gap-3">
              {!step2Open && (
                <span className="font-mono text-[11px] text-gray-500">{oralSummary}</span>
              )}
              {oralScript && <CheckCircle2 className="h-3.5 w-3.5 text-green-500" />}
              {step2Open ? (
                <ChevronUp className="h-4 w-4 text-gray-500" />
              ) : (
                <ChevronDown className="h-4 w-4 text-gray-500" />
              )}
            </div>
          </button>

          <div
            className={`overflow-hidden border-t border-gray-800 transition-all duration-300 ${
              step2Open ? 'max-h-[28rem] opacity-100' : 'max-h-0 opacity-0'
            }`}
          >
            <div className="flex flex-col gap-3 p-3">
              {isRewriting && !oralScript ? (
                <div
                  className="w-full rounded-md border border-blue-500/30 bg-[#0a0a0c] p-3"
                  style={{ minHeight: '12rem' }}
                >
                  <div className="mb-3 flex items-center gap-2">
                    <div className="h-2 w-2 rounded-full bg-blue-400 animate-pulse" />
                    <span className="text-[11px] text-blue-400">AI 正在输出口播稿…</span>
                  </div>
                  <div className="space-y-2">
                    {[100, 80, 90, 60, 75].map((width, index) => (
                      <div
                        key={index}
                        className="h-3 animate-pulse rounded bg-gray-800"
                        style={{ width: `${width}%`, animationDelay: `${index * 100}ms` }}
                      />
                    ))}
                  </div>
                </div>
              ) : (
                <textarea
                  value={oralScript}
                  onChange={(e) => setOralScript(e.target.value)}
                  disabled={isRewriting}
                  placeholder="生成后的口播稿会显示在这里，你也可以在开始分镜前手动修改。"
                  className={`w-full resize-none rounded-md border bg-[#0a0a0c] p-3 text-sm leading-relaxed transition-all focus:outline-none ${
                    isRewriting
                      ? 'border-blue-500/50 text-gray-400'
                      : 'border-gray-800 text-yellow-100 focus:border-violet-500/50'
                  }`}
                  rows={8}
                />
              )}
              <div className="flex items-center justify-between gap-3">
                <span className="text-[12px] text-gray-500">
                  确认口播稿后再生成 Timeline、预览和代码。
                </span>
                <button
                  onClick={handleGenerateVideo}
                  disabled={isGeneratingVideo || isRewriting || !oralScript.trim()}
                  className="flex items-center gap-1.5 rounded bg-violet-600 px-4 py-2.5 text-sm font-semibold text-white shadow transition-all hover:-translate-y-0.5 hover:bg-violet-500 hover:shadow-lg active:translate-y-0 disabled:opacity-50"
                >
                  {isGeneratingVideo ? (
                    <Loader2 className="h-3.5 w-3.5 animate-spin" />
                  ) : (
                    <Video className="h-3.5 w-3.5" />
                  )}
                  {isGeneratingVideo ? '正在生成分镜…' : '生成分镜与代码'}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
