import React from 'react';
import { ChevronUp, ChevronDown } from 'lucide-react';
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
  const { charCount, estimatedSec, sceneDurationSec, isTooLong } = useScriptMetrics();

  return (
    <div className="flex-shrink-0 bg-[#141416]">
      <div className="flex items-center gap-2 px-4 py-2 border-t-2 border-gray-700 bg-[#111113]">
        <span className="text-[11px] text-gray-500 uppercase tracking-[0.24em] font-semibold">当前镜头精调</span>
      </div>

      <button
        onClick={onToggle}
        className="w-full flex items-center justify-between px-4 py-3 bg-[#1c1c1f] hover:bg-[#232326] transition-colors"
      >
        <div className="flex items-center gap-2">
          <span className="text-orange-400 text-sm">{hasScenes ? '已就绪' : '未开始'}</span>
          <h3 className="text-xs text-gray-300 font-bold tracking-wide">
            {hasScenes ? (
              <>
                正在编辑
                <span className="text-orange-300 ml-1">{activeScene.componentType}</span>
              </>
            ) : (
              '请先生成 Timeline'
            )}
          </h3>
        </div>
        <div className="flex items-center gap-3">
          {hasScenes && isTooLong && (
            <span className="text-[11px] text-red-500 font-mono tracking-wide px-1.5 py-0.5 bg-red-500/10 rounded">文案偏长</span>
          )}
          {isOpen ? (
            <ChevronUp className="w-4 h-4 text-gray-500" />
          ) : (
            <ChevronDown className="w-4 h-4 text-gray-500" />
          )}
        </div>
      </button>

      {isOpen && (
        <div className="bg-[#18181b] p-3 flex flex-col gap-2">
          {!hasScenes || !activeScene.id ? (
            <div className="rounded-lg border border-dashed border-gray-700 bg-[#0e0e11] px-4 py-5">
              <p className="text-sm text-gray-300">这里会显示当前分镜的旁白文案。</p>
              <p className="mt-2 text-[12px] text-gray-500">生成 Timeline 后，你可以逐镜头调整文案长度与节奏。</p>
            </div>
          ) : (
            <>
              <textarea
                value={activeScene.script}
                onChange={(e) => updateSceneScript(activeScene.id, e.target.value)}
                placeholder="在这里编辑当前片段的旁白文案..."
                className="w-full text-sm text-gray-200 bg-[#0e0e11] p-3 rounded border border-gray-700 focus:border-green-500/50 focus:outline-none resize-none leading-relaxed"
                rows={5}
              />
              <div className="flex justify-between items-center text-[12px] font-mono">
                <span className="text-gray-500">{charCount} 字</span>
                <div className="flex items-center gap-3">
                  <span className={isTooLong ? 'text-red-400' : 'text-gray-500'}>
                    预估 {estimatedSec.toFixed(1)}s
                  </span>
                  <span className="text-gray-600">|</span>
                  <span className="text-gray-500">片段 {sceneDurationSec.toFixed(1)}s</span>
                </div>
              </div>
            </>
          )}
        </div>
      )}
    </div>
  );
};
