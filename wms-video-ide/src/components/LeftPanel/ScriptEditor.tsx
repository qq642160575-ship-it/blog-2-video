import React, { useEffect, useMemo, useState } from 'react';
import { ChevronDown, ChevronUp, Loader2, RefreshCw, Save } from 'lucide-react';
import { useIdeStore } from '../../store/useIdeStore';
import { useScriptMetrics } from '../../hooks/useScriptMetrics';
import { selectActiveScene } from '../../store/selectors';

interface ScriptEditorProps {
  isOpen: boolean;
  onToggle: () => void;
}

export const ScriptEditor: React.FC<ScriptEditorProps> = ({ isOpen, onToggle }) => {
  const hasScenes = useIdeStore((s) => s.scenes.length > 0);
  const activeScene = useIdeStore(selectActiveScene);
  const updateSceneScript = useIdeStore((s) => s.updateSceneScript);
  const animationThreadId = useIdeStore((s) => s.animationThreadId);
  const updateSceneCode = useIdeStore((s) => s.updateSceneCode);
  const updateArtifacts = useIdeStore((s) => s.updateArtifacts);
  const addProcessLog = useIdeStore((s) => s.addProcessLog);
  const setAiStatus = useIdeStore((s) => s.setAiStatus);
  const aiStatus = useIdeStore((s) => s.aiStatus);
  const captureAnimationBaseline = useIdeStore((s) => s.captureAnimationBaseline);
  const { charCount, estimatedSec, sceneDurationSec, isTooLong } = useScriptMetrics();

  const [draftScript, setDraftScript] = useState('');
  const [draftDesign, setDraftDesign] = useState('');

  useEffect(() => {
    if (!activeScene.id) {
      setDraftScript('');
      setDraftDesign('');
      return;
    }

    setDraftScript(activeScene.script);
    setDraftDesign(activeScene.visual_design || '');
  }, [activeScene.id, activeScene.script, activeScene.visual_design]);

  const isGenerating = aiStatus === 'generating';
  const isDirty = useMemo(
    () =>
      !!activeScene.id &&
      (draftScript !== activeScene.script || draftDesign !== (activeScene.visual_design || '')),
    [activeScene.id, activeScene.script, activeScene.visual_design, draftDesign, draftScript]
  );

  const applyChanges = () => {
    if (!activeScene.id) return;
    updateSceneScript(activeScene.id, draftScript, draftDesign);
    addProcessLog(`已保存镜头 ${activeScene.id} 的文案和视觉说明。`);
  };

  const [recompileFrom, setRecompileFrom] = useState<'layout' | 'motion' | 'dsl' | 'code'>('layout');

  const handleRegenerate = async (from: 'layout'|'motion'|'dsl'|'code' = recompileFrom) => {
    if (!activeScene.id) return;

    updateSceneScript(activeScene.id, draftScript, draftDesign);

    if (!animationThreadId) {
      addProcessLog('无法局部重算：缺少当前动画线程 ID。');
      return;
    }

    setAiStatus('generating');
    addProcessLog(`开始局部重算镜头：${activeScene.id}`);

    try {
      const response = await fetch('/api/workflows/animation/regenerate_scene_sse', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          thread_id: animationThreadId,
          scene_id: activeScene.id,
          oral_script: draftScript,
          recompile_from: from,
        }),
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const { readSse } = await import('../../utils/sse');
      await readSse(response, (payload) => {
        if (payload.type === 'error') {
          throw new Error(payload.message || '局部重算失败');
        }

        if (payload.type === 'end') {
          if (payload.status === 'error') {
            throw new Error(payload.progress?.description || '局部重算失败');
          }
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

          addProcessLog(`局部重算完成节点：${nodeName}`);

          if (nodeName === 'compile_layout_node' && nodeData.layouts) {
            updateArtifacts({ layouts: nodeData.layouts });
          }

          if (nodeName === 'compile_motion_node' && nodeData.motions) {
            updateArtifacts({ motions: nodeData.motions });
          }

          if (nodeName === 'generate_dsl_node' && nodeData.dsl) {
            updateArtifacts({ dsl: nodeData.dsl });
          }

          if ((nodeName === 'generate_scene_code_node' || nodeName === 'repair_scene_node') && nodeData.codes) {
            const allCodes = nodeData.codes;
            updateArtifacts({ codes: allCodes });
            Object.keys(allCodes).forEach((sid) => {
              if (sid === activeScene.id) {
                updateSceneCode(sid, allCodes[sid].code);
                addProcessLog(`已更新镜头 ${sid} 的重新编译代码。`);
              }
            });
          }

          if (nodeData.validations) {
            updateArtifacts({ validations: nodeData.validations });
          }
        }
      });

      setAiStatus('idle');
      addProcessLog(`局部重算完成：${activeScene.id}`);
      captureAnimationBaseline();
    } catch (error) {
      addProcessLog(`局部重算失败：${(error as Error).message}`);
      setAiStatus('error');
    }
  };

  if (!hasScenes) {
    return null;
  }

  return (
    <div className="flex-shrink-0 bg-[#141416]">
      <div className="flex items-center gap-2 border-t-2 border-gray-700 bg-[#111113] px-4 py-2">
        <span className="text-[11px] font-semibold uppercase tracking-[0.24em] text-gray-500">
          当前镜头编辑
        </span>
      </div>

      <button
        onClick={onToggle}
        className="flex w-full items-center justify-between bg-[#1c1c1f] px-4 py-3 transition-colors hover:bg-[#232326]"
      >
        <div className="flex items-center gap-2">
          <span className="text-sm text-orange-400">镜头 {activeScene.componentType}</span>
          <h3 className="text-xs font-bold tracking-wide text-gray-300">单一编辑入口</h3>
        </div>
        <div className="flex items-center gap-3">
          {isTooLong && (
            <span className="rounded bg-red-500/10 px-1.5 py-0.5 text-[11px] font-mono tracking-wide text-red-500">
              文案偏长
            </span>
          )}
          {isOpen ? (
            <ChevronUp className="h-4 w-4 text-gray-500" />
          ) : (
            <ChevronDown className="h-4 w-4 text-gray-500" />
          )}
        </div>
      </button>

      {isOpen && (
        <div className="flex flex-col gap-3 bg-[#18181b] p-3">
          <div>
            <p className="mb-2 text-[12px] font-medium text-gray-300">旁白文案</p>
            <textarea
              value={draftScript}
              onChange={(e) => setDraftScript(e.target.value)}
              placeholder="编辑当前镜头的旁白文案。"
              className="w-full resize-none rounded border border-gray-700 bg-[#0e0e11] p-3 text-sm leading-relaxed text-gray-200 focus:border-green-500/50 focus:outline-none"
              rows={5}
            />
          </div>

          <div>
            <p className="mb-2 text-[12px] font-medium text-gray-300">视觉说明</p>
            <textarea
              value={draftDesign}
              onChange={(e) => setDraftDesign(e.target.value)}
              placeholder="补充当前镜头的视觉设计要求。"
              className="w-full resize-none rounded border border-gray-700 bg-[#0e0e11] p-3 text-sm leading-relaxed text-gray-200 focus:border-green-500/50 focus:outline-none"
              rows={4}
            />
          </div>

          <div className="flex items-center justify-between text-[12px] font-mono">
            <span className="text-gray-500">{charCount} 字</span>
            <div className="flex items-center gap-3">
              <span className={isTooLong ? 'text-red-400' : 'text-gray-500'}>
                预计 {estimatedSec.toFixed(1)}s
              </span>
              <span className="text-gray-600">|</span>
              <span className="text-gray-500">镜头 {sceneDurationSec.toFixed(1)}s</span>
            </div>
          </div>

          <div className="flex flex-col gap-2 rounded border border-gray-800 bg-[#111113] px-3 py-2">
            <p className="text-[12px] text-gray-500">
              先保存文案，再选择进行对应级别的重算。不同的重算会经过不同的节点。
            </p>
            <div className="flex items-center gap-2">
              <button
                onClick={applyChanges}
                disabled={!isDirty || isGenerating}
                className="flex items-center gap-1.5 rounded border border-gray-700 px-3 py-1.5 text-[11px] text-gray-200 transition-colors hover:bg-gray-800 disabled:opacity-50"
              >
                <Save className="h-3 w-3" />
                仅保存草稿
              </button>
              
              <div className="h-4 w-[1px] bg-gray-700 mx-1"></div>

              <select
                value={recompileFrom}
                onChange={(e) => setRecompileFrom(e.target.value as any)}
                className="bg-gray-800 text-gray-200 border border-gray-700 rounded px-2 py-1 text-[11px] outline-none"
              >
                <option value="layout">从 Layout 重算</option>
                <option value="motion">从 Motion 重算</option>
                <option value="dsl">从 DSL 重算</option>
                <option value="code">仅重新生成 Code</option>
              </select>

              <button
                onClick={() => handleRegenerate(recompileFrom)}
                disabled={isGenerating || !draftScript.trim()}
                className="flex items-center gap-1.5 rounded bg-violet-600 px-3 py-1.5 text-[11px] font-semibold text-white transition-colors hover:bg-violet-500 disabled:opacity-50"
              >
                {isGenerating ? (
                  <Loader2 className="h-3 w-3 animate-spin" />
                ) : (
                  <RefreshCw className="h-3 w-3" />
                )}
                执行重算
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
