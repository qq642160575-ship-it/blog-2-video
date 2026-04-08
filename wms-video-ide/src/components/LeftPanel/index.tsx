import React, { useState } from 'react';
import { Sparkles } from 'lucide-react';
import { SourceInput } from './SourceInput';
import { Timeline } from './Timeline';
import { ScriptEditor } from './ScriptEditor';

/**
 * 左侧面板组合容器。
 * - 持有 scriptPanelOpen 这个纯 UI 状态（不需要跨组件，不需要入 store）
 * - 三个子区域：博文输入 / Timeline / 文案编辑台
 */
export const LeftPanel: React.FC = () => {
  const [scriptPanelOpen, setScriptPanelOpen] = useState(true);

  return (
    <div className="w-[25%] border-r border-gray-800 flex flex-col bg-[#18181b] min-h-0">
      {/* 顶部 Logo */}
      <div className="p-4 border-b border-gray-800 flex items-center gap-2 flex-shrink-0">
        <Sparkles className="w-5 h-5 text-purple-500" />
        <h2 className="font-bold text-gray-100 text-sm">AI-Code-Video IDE</h2>
      </div>

      {/* 上半区：博文原文 + Timeline（可滚动） */}
      <div className="flex-1 overflow-y-auto p-4 flex flex-col gap-4 min-h-0">
        <SourceInput />
        <Timeline />
      </div>

      {/* 下半区：可折叠文案编辑台 */}
      <ScriptEditor
        isOpen={scriptPanelOpen}
        onToggle={() => setScriptPanelOpen((v) => !v)}
      />
    </div>
  );
};
