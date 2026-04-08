import React, { useCallback } from 'react';
import Editor from '@monaco-editor/react';
import { Code2 } from 'lucide-react';
import { useIdeStore } from '../../store/useIdeStore';
import { selectActiveScene } from '../../store/selectors';

/**
 * Monaco Editor 封装。
 * - 精确订阅 activeScene，仅 code 变化时重渲染
 * - onChange 用 useCallback 稳定引用，防止 Editor 内部不必要更新
 */
export const CodeEditor: React.FC = () => {
  const activeScene = useIdeStore(selectActiveScene);
  const activeSceneId = useIdeStore((s) => s.activeSceneId);
  const updateSceneCode = useIdeStore((s) => s.updateSceneCode);

  const handleChange = useCallback(
    (val: string | undefined) => {
      updateSceneCode(activeSceneId, val ?? '');
    },
    [activeSceneId, updateSceneCode]
  );

  return (
    <div className="w-[40%] flex flex-col bg-[#1e1e1e]">
      {/* 顶栏 */}
      <div className="px-4 py-3 border-b border-gray-800 flex items-center justify-between bg-[#18181b] flex-shrink-0">
        <div className="flex items-center gap-2">
          <Code2 className="w-4 h-4 text-blue-400" />
          <span className="text-xs font-semibold text-gray-300">GeneratedScene.tsx</span>
        </div>
        <span className="text-[10px] bg-blue-500/10 text-blue-400 px-2 py-1 rounded border border-blue-500/20">
          Auto-Sync
        </span>
      </div>

      {/* Editor */}
      <div className="flex-1 min-h-0">
        <Editor
          height="100%"
          defaultLanguage="javascript"
          theme="vs-dark"
          value={activeScene.code}
          onChange={handleChange}
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
  );
};
