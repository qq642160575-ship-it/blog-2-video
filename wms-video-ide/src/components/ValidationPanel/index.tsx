import React from 'react';
import { AlertCircle, CheckCircle2, Wrench, Loader2 } from 'lucide-react';
import { useIdeStore } from '../../store/useIdeStore';

export const ValidationPanel: React.FC = () => {
  const activeSceneId = useIdeStore((s) => s.activeSceneId);
  const validations = useIdeStore((s) => s.validations);
  const aiStatus = useIdeStore((s) => s.aiStatus);
  const animationThreadId = useIdeStore((s) => s.animationThreadId);
  const updateSceneCode = useIdeStore((s) => s.updateSceneCode);
  const updateArtifacts = useIdeStore((s) => s.updateArtifacts);
  const addProcessLog = useIdeStore((s) => s.addProcessLog);
  const setAiStatus = useIdeStore((s) => s.setAiStatus);
  const isGenerating = aiStatus === 'generating';

  if (!activeSceneId) {
    return (
      <div className="flex h-full items-center justify-center text-sm text-gray-500">
        等待分镜输入
      </div>
    );
  }

  const validation = validations[activeSceneId];

  const handleRepair = async () => {
    if (!animationThreadId || !activeSceneId) return;

    setAiStatus('generating');
    addProcessLog(`开始对镜头 ${activeSceneId} 执行自动修复。`);

    try {
      const response = await fetch('/api/workflows/animation/recompile_layout_sse', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          thread_id: animationThreadId,
          scene_id: activeSceneId,
          recompile_from: 'layout',
        }),
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const { readSse } = await import('../../utils/sse');
      await readSse(response, (payload) => {
        if (payload.type === 'error') {
          throw new Error(payload.message || '自动修复失败');
        }

        if (payload.type === 'end') {
          if (payload.status === 'error') {
            throw new Error(payload.progress?.description || '自动修复失败');
          }
          return;
        }

        if (payload.type !== 'updates' || !payload.data) return;
        const updateData =
          payload.data.type === 'updates' && payload.data.data ? payload.data.data : payload.data;
        const nodeName = Object.keys(updateData)[0];
        const nodeData = updateData[nodeName];
        if (!nodeName || !nodeData) return;

        if (nodeData.layouts) updateArtifacts({ layouts: nodeData.layouts });
        if (nodeData.motions) updateArtifacts({ motions: nodeData.motions });
        if (nodeData.dsl) updateArtifacts({ dsl: nodeData.dsl });
        if (nodeData.codes) {
          updateArtifacts({ codes: nodeData.codes });
          Object.values(nodeData.codes).forEach((coder: any) => {
            updateSceneCode(coder.scene_id, coder.code);
          });
        }
        if (nodeData.validations) updateArtifacts({ validations: nodeData.validations });
      });

      addProcessLog(`镜头 ${activeSceneId} 自动修复完成。`);
      setAiStatus('idle');
    } catch (error) {
      addProcessLog(`自动修复失败：${(error as Error).message}`);
      setAiStatus('error');
    }
  };

  if (!validation) {
    return (
      <div className="flex p-4 text-sm text-gray-400">
        <CheckCircle2 className="mr-2 text-gray-600 h-5 w-5" />
        当前镜头尚未进行校验
      </div>
    );
  }

  if (validation.status === 'pass') {
    return (
      <div className="flex p-4 text-sm text-green-400 bg-green-500/10 m-4 rounded">
        <CheckCircle2 className="mr-2 h-5 w-5" />
        分镜 {activeSceneId} 校验通过 (阶段: {validation.stage})
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full bg-[#1e1e1e]">
      <div className="border-b border-gray-800 bg-[#18181b] px-4 py-3 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <AlertCircle className="h-4 w-4 text-red-400" />
          <span className="text-xs font-semibold text-gray-300">缺陷隔离面版</span>
        </div>
        <span className="text-[11px] px-2 py-0.5 rounded bg-red-500/20 text-red-400 border border-red-500/30">
          Validation Failed
        </span>
      </div>
      
      <div className="flex-1 overflow-auto p-4 space-y-4">
        {validation.errors.map((err, idx) => (
          <div key={idx} className="bg-[#111113] p-4 rounded-lg border border-red-900/50 flex flex-col gap-3">
            <div className="flex items-start gap-3">
              <div className="p-1.5 bg-red-500/10 rounded">
                <AlertCircle className="h-4 w-4 text-red-400" />
              </div>
              <div className="flex-1">
                <h4 className="text-sm font-bold text-gray-200">{err.code}</h4>
                <p className="mt-1 text-xs text-gray-400">{err.message}</p>
                {err.stage && <p className="mt-2 text-[10px] text-gray-500 font-mono">Stage: {err.stage}</p>}
              </div>
            </div>

            {validation.repairable && (
              <div className="mt-2 pt-3 border-t border-gray-800 flex justify-end">
                <button
                  onClick={handleRepair}
                  disabled={isGenerating}
                  className="flex items-center gap-2 bg-blue-600/20 hover:bg-blue-600/40 border border-blue-500/30 text-blue-400 px-3 py-1.5 rounded text-xs transition-colors disabled:opacity-50"
                >
                  {isGenerating ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Wrench className="w-3.5 h-3.5" />}
                  执行自愈降级
                </button>
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
};
