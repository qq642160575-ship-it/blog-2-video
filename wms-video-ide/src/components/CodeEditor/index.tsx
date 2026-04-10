import React, { useCallback, useEffect, useRef, useState } from 'react';
import Editor from '@monaco-editor/react';
import { Code2, TerminalSquare, Loader2, ChevronDown, ChevronRight } from 'lucide-react';
import { useIdeStore } from '../../store/useIdeStore';
import { selectActiveScene } from '../../store/selectors';

/**
 * Monaco Editor 封装。
 * - 精确订阅 activeScene，仅 code 变化时重渲染
 * - onChange 用 useCallback 稳定引用，防止 Editor 内部不必要更新
 */
const LogItem: React.FC<{ log: { time: string; content: string; details?: string } }> = ({ log }) => {
  const [expanded, setExpanded] = useState(false);

  return (
    <div className="mb-1.5 leading-relaxed">
      <div className="flex items-start">
        <span className="text-gray-600 mr-2 shrink-0">[{log.time}]</span>
        <div className="flex-1 flex items-start gap-1">
          <span className={log.content.includes('❌') ? 'text-red-400' : log.content.includes('✅') ? 'text-green-400' : 'text-gray-300'}>
            {log.content}
          </span>
          {log.details && (
            <button onClick={() => setExpanded(!expanded)} className="mt-0.5 text-gray-500 hover:text-gray-300 transition-colors">
              {expanded ? <ChevronDown className="w-3 h-3" /> : <ChevronRight className="w-3 h-3" />}
            </button>
          )}
        </div>
      </div>
      {log.details && expanded && (
        <div className="mt-1 ml-[60px] p-2 bg-[#18181b] rounded text-gray-400 border border-gray-800 break-all whitespace-pre-wrap text-[11px] leading-relaxed">
          {log.details}
        </div>
      )}
    </div>
  );
};
export const CodeEditor: React.FC = () => {
  const activeScene = useIdeStore(selectActiveScene);
  const activeSceneId = useIdeStore((s) => s.activeSceneId);
  const updateSceneCode = useIdeStore((s) => s.updateSceneCode);
  const processLogs = useIdeStore((s) => s.processLogs);
  const rewriteStatus = useIdeStore((s) => s.rewriteStatus);
  const processStartTime = useIdeStore((s) => s.processStartTime);

  const [elapsed, setElapsed] = useState(0);
  const logsEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (rewriteStatus === 'generating' && processStartTime) {
      const timer = setInterval(() => {
        setElapsed(Math.floor((Date.now() - processStartTime) / 1000));
      }, 1000);
      return () => clearInterval(timer);
    } else {
      setElapsed(0);
    }
  }, [rewriteStatus, processStartTime]);

  useEffect(() => {
    logsEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [processLogs]);

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

      {/* Editor区 (上半部分) */}
      <div className="flex-1 min-h-0 border-b border-gray-800">
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

      {/* 流程日志区 (下半部分) */}
      <div className="h-64 bg-[#0e0e11] flex flex-col flex-shrink-0">
        <div className="px-4 py-2 border-b border-gray-800 flex items-center justify-between bg-[#18181b]">
          <div className="flex items-center gap-2">
            <TerminalSquare className="w-4 h-4 text-green-400" />
            <span className="text-[10px] font-semibold text-gray-400 uppercase tracking-wider">Execution Logs</span>
          </div>
          {rewriteStatus === 'generating' && (
             <span className="text-xs text-blue-400 flex items-center gap-1">
               <Loader2 className="w-3 h-3 animate-spin" />
               正在执行: {elapsed}s
             </span>
          )}
        </div>
        <div className="flex-1 overflow-y-auto p-3 text-xs font-mono">
          {processLogs.length === 0 ? (
            <div className="text-gray-600 italic">任务日志将在此展示...</div>
          ) : (
            processLogs.map((log, i) => (
              <LogItem key={i} log={log} />
            ))
          )}
          <div ref={logsEndRef} />
        </div>
      </div>
    </div>
  );
};
