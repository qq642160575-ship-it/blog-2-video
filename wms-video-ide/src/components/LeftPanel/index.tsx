import React, { useState } from 'react';
import { Sparkles } from 'lucide-react';
import { SourceInput } from './SourceInput';
import { Timeline } from './Timeline';
import { ScriptEditor } from './ScriptEditor';
import { WorkflowStatus } from './WorkflowStatus';
import { ArtifactTabs } from './ArtifactTabs';
import { useIdeStore } from '../../store/useIdeStore';

export const LeftPanel: React.FC = () => {
  const [scriptPanelOpen, setScriptPanelOpen] = useState(false);
  const hasScenes = useIdeStore((s) => s.scenes.length > 0);

  return (
    <div className="flex min-h-0 w-[30%] flex-col overflow-hidden border-r border-gray-800 bg-[#18181b]">
      <div className="flex flex-shrink-0 items-center gap-2 border-b border-gray-800 p-4">
        <Sparkles className="h-5 w-5 text-violet-500" />
        <div>
          <h2 className="text-sm font-bold text-gray-100">AI Code Video IDE</h2>
          <p className="mt-1 text-[12px] text-gray-500">按顺序完成原文、口播稿、分镜和代码。</p>
        </div>
      </div>

      <div className="flex min-h-0 flex-1 flex-col gap-4 overflow-hidden p-4">
        <WorkflowStatus />
        <SourceInput />
        <ArtifactTabs />
        <Timeline />
      </div>

      {hasScenes && (
        <ScriptEditor
          isOpen={scriptPanelOpen}
          onToggle={() => setScriptPanelOpen((value) => !value)}
        />
      )}
    </div>
  );
};
