import React from 'react';
import { FileText, ChevronUp, ChevronDown } from 'lucide-react';
import { useIdeStore } from '../../store/useIdeStore';
import { useScriptMetrics } from '../../hooks/useScriptMetrics';

interface ScriptEditorProps {
  isOpen: boolean;
  onToggle: () => void;
}

/**
 * 文案编辑台。
 * - 消费 selectActiveScene selector，精确订阅
 * - 字数/时长指标通过 useScriptMetrics hook 获取，不在组件体内重复计算
 */
export const ScriptEditor: React.FC<ScriptEditorProps> = ({ isOpen, onToggle }) => {
  // 不能用 selectActiveScene 直接传给 useIdeStore：.find() 每次返回新对象引用
  // → Zustand Object.is 永远不等 → 无限 rerender。改为订阅标量字段。
  const activeSceneId = useIdeStore((s) => s.activeSceneId);
  const activeScene = useIdeStore((s) => s.scenes.find((x) => x.id === s.activeSceneId) ?? s.scenes[0]);
  const updateSceneScript = useIdeStore((s) => s.updateSceneScript);
  const { charCount, estimatedSec, sceneDurationSec, isTooLong } = useScriptMetrics();

  return (
    <div className="flex-shrink-0 border-t border-gray-700 bg-[#141416]">
      {/* 折叠标题栏 */}
      <button
        onClick={onToggle}
        className="w-full flex items-center justify-between px-4 py-3 bg-[#1c1c1f] hover:bg-[#232326] transition-colors"
      >
        <div className="flex items-center gap-2">
          <span className="flex items-center justify-center w-5 h-5 rounded-full bg-orange-500/10 text-orange-400 text-[10px] font-bold">4</span>
          <h3 className="text-xs text-gray-300 font-bold tracking-wide flex items-center gap-2">
            当前分镜文案
            <span className="text-[9px] bg-[#27272a] text-gray-300 px-1.5 py-0.5 rounded font-normal">
              {activeScene.componentType}
            </span>
          </h3>
        </div>
        <div className="flex items-center gap-3">
          {isTooLong && (
            <span className="text-[9px] text-red-500 font-mono tracking-wide px-1.5 py-0.5 bg-red-500/10 rounded">⚠ 文案偏长</span>
          )}
          {isOpen ? (
            <ChevronDown className="w-4 h-4 text-gray-500" />
          ) : (
            <ChevronUp className="w-4 h-4 text-gray-500" />
          )}
        </div>
      </button>

      {/* 可折叠内容区 */}
      {isOpen && (
        <div className="bg-[#18181b] p-3 flex flex-col gap-2">
          <textarea
            value={activeScene.script}
            onChange={(e) => updateSceneScript(activeScene.id, e.target.value)}
            placeholder="在这里编辑当前片段的旁白文案..."
            className="w-full text-sm text-gray-200 bg-[#0e0e11] p-3 rounded border border-gray-700 focus:border-green-500/50 focus:outline-none resize-none leading-relaxed"
            rows={4}
          />
          {/* 底部辅助信息 */}
          <div className="flex justify-between items-center text-[10px] font-mono">
            <span className="text-gray-500">{charCount} 字</span>
            <div className="flex items-center gap-3">
              <span className={isTooLong ? 'text-red-400' : 'text-gray-500'}>
                预估 {estimatedSec.toFixed(1)}s
              </span>
              <span className="text-gray-600">|</span>
              <span className="text-gray-500">片段 {sceneDurationSec.toFixed(1)}s</span>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
