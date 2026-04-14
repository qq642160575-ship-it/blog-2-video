import React, { useState } from 'react';
import {
  CheckCircle2,
  ChevronDown,
  ChevronUp,
  Loader2,
  Sparkles,
  Video,
} from 'lucide-react';
import { useIdeStore } from '../../store/useIdeStore';
import { getNodePresentation } from '../../utils/workflowUi';
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

type SsePayload = {
  type: string;
  status?: 'success' | 'partial_success' | 'error';
  message?: string;
  data?: Record<string, any>;
  thread_id?: string;
  checkpoint_id?: string | null;
  workflow?: WorkflowName;
  progress?: ServerProgress;
};

export const SourceInput: React.FC = () => {
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
  const setScenes = useIdeStore((s) => s.setScenes);
  const updateSceneCode = useIdeStore((s) => s.updateSceneCode);
  const updateArtifacts = useIdeStore((s) => s.updateArtifacts);
  const scriptThreadId = useIdeStore((s) => s.scriptThreadId);
  const animationThreadId = useIdeStore((s) => s.animationThreadId);
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

  const readSse = async (
    response: Response,
    onPayload: (payload: SsePayload) => void
  ) => {
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

        try {
          onPayload(JSON.parse(dataStr));
        } catch (error) {
          console.warn('解析 SSE 数据失败:', dataStr, error);
        }
      }
    }
  };

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
      const response = await fetch('/api/generate_script_sse', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          source_text: sourceText,
          thread_id: scriptThreadId,
        }),
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      await readSse(response, (payload) => {
        if (payload.thread_id) {
          setScriptThreadContext(payload.thread_id, payload.checkpoint_id ?? undefined);
        }

        if (payload.progress) {
          applyServerProgress('conversational_tone', payload.progress);
        }

        if (payload.type === 'progress') {
          return;
        }

        if (payload.type === 'setup') {
          setWorkflowProgress('conversational_tone', {
            status: 'running',
            nodeLabel: '正在生成口播脚本',
            description: '已连接到口播脚本生成任务。',
            lastError: null,
          });
          addProcessLog('已连接口播稿工作流。');
          return;
        }

        if (payload.type === 'end') {
          if (payload.checkpoint_id) {
            setScriptThreadContext(payload.thread_id ?? scriptThreadId, payload.checkpoint_id);
          }
          setWorkflowProgress('conversational_tone', {
            status: payload.status === 'error' ? 'error' : 'success',
            description:
              payload.status === 'error'
                ? '口播脚本生成失败，请重试。'
                : '口播脚本生成完成，可以继续进入分镜阶段。',
            lastError: null,
          });
          addProcessLog('口播稿工作流结束。');
          if (payload.status === 'error') {
            throw new Error(payload.progress?.description || '口播稿生成失败');
          }
          return;
        }

          if (payload.type === 'error') {
            setWorkflowProgress('conversational_tone', {
              status: 'error',
              description: '口播脚本生成失败，请检查网络或稍后重试。',
              lastError: payload.message || '口播脚本生成失败',
            });
            throw new Error(payload.message || '口播稿生成失败');
          }

        if (payload.type === 'updates' && payload.data) {
          let updateData = payload.data;
          if (updateData.type === 'updates' && updateData.data) {
            updateData = updateData.data;
          }

          const nodeName = Object.keys(updateData)[0];
          const nodeData = updateData[nodeName];
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

          if (nodeName === 'finalize_oral_script_node' && nodeData.oral_script_result) {
            setOralScript(nodeData.oral_script_result.oral_script || '');
            updateArtifacts({
              parsedScript: {
                source_id: 'oral-script',
                intent: 'oral_script',
                tone: nodeData.oral_script_result.script_metadata?.tone || 'conversational',
                emotion_curve: [],
                segments: nodeData.oral_script_result.script_segments || [],
              },
            });
            addProcessLog('已生成结构化口语稿结果。');
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
      const response = await fetch('/api/generate_animation_sse', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          oral_script: oralScript,
          thread_id: animationThreadId,
        }),
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      await readSse(response, (payload) => {
        if (payload.thread_id) {
          setAnimationThreadContext(payload.thread_id, payload.checkpoint_id ?? undefined);
        }

        if (payload.progress) {
          applyServerProgress('animation', payload.progress);
        }

        if (payload.type === 'progress') {
          return;
        }

        if (payload.type === 'setup') {
          addProcessLog('已连接视频工作流。');
          return;
        }

        if (payload.type === 'end') {
          if (payload.checkpoint_id) {
            setAnimationThreadContext(
              payload.thread_id ?? animationThreadId,
              payload.checkpoint_id
            );
          }
          setWorkflowProgress('animation', {
            status: payload.status === 'error' ? 'error' : 'success',
            description:
              payload.status === 'partial_success'
                ? '部分镜头生成失败，但其余结果已可预览。'
                : payload.status === 'error'
                  ? '视频工作流失败，请检查日志后重试。'
                  : '视频工作流结束。',
            lastError:
              payload.status === 'error' ? payload.progress?.description || '视频生成失败' : null,
          });
          addProcessLog(
            payload.status === 'partial_success' ? '视频工作流部分完成。' : '视频工作流结束。'
          );
          if (payload.status === 'error') {
            throw new Error(payload.progress?.description || '视频生成失败');
          }
          return;
        }

        if (payload.type === 'error') {
          throw new Error(payload.message || '视频生成失败');
        }

        if (payload.type === 'updates' && payload.data) {
          let updateData = payload.data;
          if (updateData.type === 'updates' && updateData.data) {
            updateData = updateData.data;
          }

          const nodeName = Object.keys(updateData)[0];
          const nodeData = updateData[nodeName];
          if (!nodeName || !nodeData) return;

          addProcessLog(`节点完成：${nodeName}`);
          
          if (nodeName === 'parse_oral_script_node' && nodeData.parsed_script) {
             updateArtifacts({ parsedScript: nodeData.parsed_script });
          }
          
          if (nodeName === 'plan_scenes_node' && nodeData.scenes) {
             updateArtifacts({ scenePlan: nodeData.scenes });
          }

          if (nodeName === 'generate_marks_node' && nodeData.scenes) {
            updateArtifacts({ marks: nodeData.marks });
            const parsedScenes = nodeData.scenes.map((scene: any) => ({
              id: scene.scene_id,
              durationInFrames: scene.duration_in_frames || ((scene.end || 30) - (scene.start || 0)),
              componentType: scene.scene_id.replace(/\s+/g, ''),
              script: scene.text,
              visual_design: scene.visual_goal || '',
              marks: nodeData.marks?.scene_marks?.[scene.scene_id] || {},
              code: '// 正在等待 Compiler 生成模板化代码...',
            }));
            setScenes(parsedScenes);
            addProcessLog(`已生成 ${parsedScenes.length} 个分镜。`);
          }

          if (nodeName === 'compile_layout_node' && nodeData.layouts) {
            updateArtifacts({ layouts: nodeData.layouts });
            addProcessLog(
              '已完成所有分镜的空间布局与安全区打包。',
               JSON.stringify(Object.keys(nodeData.layouts))
            );
          }
          
          if (nodeName === 'compile_motion_node' && nodeData.motions) {
            updateArtifacts({ motions: nodeData.motions });
          }

          if (nodeName === 'generate_dsl_node' && nodeData.dsl) {
            updateArtifacts({ dsl: nodeData.dsl });
          }

          if (nodeName === 'generate_scene_code_node' && nodeData.codes) {
            const allCodes = nodeData.codes;
            updateArtifacts({ codes: allCodes });
            Object.keys(allCodes).forEach((sid) => {
              updateSceneCode(sid, allCodes[sid].code);
              addProcessLog(`模板化代码已生成：${sid}`);
            });
          }
          
          if (nodeName === 'validate_scene_node' && nodeData.validations) {
            updateArtifacts({ validations: nodeData.validations });
          }
          
          if (nodeName === 'repair_scene_node') {
            if (nodeData.layouts) updateArtifacts({ layouts: nodeData.layouts });
            if (nodeData.motions) updateArtifacts({ motions: nodeData.motions });
            if (nodeData.dsl) updateArtifacts({ dsl: nodeData.dsl });
            if (nodeData.codes) {
              updateArtifacts({ codes: nodeData.codes });
              Object.keys(nodeData.codes).forEach((sid) => updateSceneCode(sid, nodeData.codes[sid].code));
            }
            if (nodeData.validations) updateArtifacts({ validations: nodeData.validations });
            if (nodeData.failed_scenes?.length) {
              addProcessLog(`遇到修复无法通过的失败节点: ${nodeData.failed_scenes.join(', ')}`);
            }
          }
        }
      });

      setAiStatus('idle');
      addProcessLog('分镜与代码生成完成。');
      captureAnimationBaseline();
      setProcessStartTime(null);
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
