import React, { useCallback, useEffect, useRef, useState } from 'react';
import Editor from '@monaco-editor/react';
import {
  Code2,
  TerminalSquare,
  Loader2,
  ChevronDown,
  ChevronRight,
  RotateCcw,
  History,
  RefreshCw,
} from 'lucide-react';
import { useIdeStore } from '../../store/useIdeStore';
import { selectActiveScene } from '../../store/selectors';
import type { WorkflowHistoryItem, WorkflowName } from '../../types/workflow';

const LogItem: React.FC<{
  log: { time: string; content: string; details?: string };
  onRetry?: () => void;
}> = ({ log, onRetry }) => {
  const [expanded, setExpanded] = useState(false);

  return (
    <div className="mb-1.5 leading-relaxed">
      <div className="flex items-start gap-1">
        <span className="text-gray-600 mr-1 shrink-0">[{log.time}]</span>
        <div className="flex-1 flex items-start gap-1 min-w-0">
          <span className="flex-1 break-words text-gray-300">{log.content}</span>
          {onRetry && (
            <button
              onClick={onRetry}
              className="shrink-0 flex items-center gap-1 text-[11px] text-blue-400 hover:text-blue-300 border border-blue-500/30 hover:border-blue-400/60 px-2 py-1 rounded transition-all hover:bg-blue-500/10 ml-1"
              title="重试"
            >
              <RotateCcw className="w-3 h-3" />
              重试
            </button>
          )}
          {log.details && (
            <button
              onClick={() => setExpanded((v) => !v)}
              className="shrink-0 mt-0.5 p-1 text-gray-500 hover:text-gray-300 transition-colors"
            >
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

const HistoryRow: React.FC<{
  item: WorkflowHistoryItem;
  onReplay: (checkpointId: string) => void;
}> = ({ item, onReplay }) => {
  return (
    <div className="rounded border border-gray-800 bg-[#111113] px-3 py-2">
      <div className="flex items-center justify-between gap-3">
        <div className="min-w-0">
          <div className="text-[11px] text-gray-300 font-mono truncate">
            {item.checkpoint_id}
          </div>
          <div className="text-[10px] text-gray-500 mt-1">
            step {item.step ?? '-'} · next: {item.next_nodes.join(', ') || 'END'}
          </div>
        </div>
        <button
          onClick={() => onReplay(item.checkpoint_id)}
          className="text-[11px] shrink-0 text-blue-300 border border-blue-500/30 hover:border-blue-400/60 px-2 py-1 rounded hover:bg-blue-500/10 transition-colors"
        >
          从此重放
        </button>
      </div>
    </div>
  );
};

export const CodeEditor: React.FC = () => {
  const activeScene = useIdeStore(selectActiveScene);
  const activeSceneId = useIdeStore((s) => s.activeSceneId);
  const hasScenes = useIdeStore((s) => s.scenes.length > 0);
  const updateSceneCode = useIdeStore((s) => s.updateSceneCode);
  const processLogs = useIdeStore((s) => s.processLogs);
  const rewriteStatus = useIdeStore((s) => s.rewriteStatus);
  const aiStatus = useIdeStore((s) => s.aiStatus);
  const processStartTime = useIdeStore((s) => s.processStartTime);
  const sourceText = useIdeStore((s) => s.sourceText);
  const oralScript = useIdeStore((s) => s.oralScript);
  const setRewriteStatus = useIdeStore((s) => s.setRewriteStatus);
  const setAiStatus = useIdeStore((s) => s.setAiStatus);
  const clearProcessLogs = useIdeStore((s) => s.clearProcessLogs);
  const addProcessLog = useIdeStore((s) => s.addProcessLog);
  const setProcessStartTime = useIdeStore((s) => s.setProcessStartTime);
  const setOralScript = useIdeStore((s) => s.setOralScript);
  const setScenes = useIdeStore((s) => s.setScenes);
  const scriptThreadId = useIdeStore((s) => s.scriptThreadId);
  const animationThreadId = useIdeStore((s) => s.animationThreadId);
  const setScriptThreadContext = useIdeStore((s) => s.setScriptThreadContext);
  const setAnimationThreadContext = useIdeStore((s) => s.setAnimationThreadContext);
  const historyWorkflow = useIdeStore((s) => s.historyWorkflow);
  const historyItems = useIdeStore((s) => s.historyItems);
  const historyLoading = useIdeStore((s) => s.historyLoading);
  const setHistoryWorkflow = useIdeStore((s) => s.setHistoryWorkflow);
  const setHistoryItems = useIdeStore((s) => s.setHistoryItems);
  const setHistoryLoading = useIdeStore((s) => s.setHistoryLoading);

  const [elapsed, setElapsed] = useState(0);
  const logsEndRef = useRef<HTMLDivElement>(null);

  const isGenerating = rewriteStatus === 'generating' || aiStatus === 'generating';
  const activeTask =
    rewriteStatus === 'generating'
      ? '口语稿'
      : aiStatus === 'generating'
        ? '视频'
        : rewriteStatus === 'error'
          ? '口语稿'
          : aiStatus === 'error'
            ? '视频'
            : null;

  useEffect(() => {
    if (isGenerating && processStartTime) {
      const timer = setInterval(() => {
        setElapsed(Math.floor((Date.now() - processStartTime) / 1000));
      }, 1000);
      return () => clearInterval(timer);
    }
    setElapsed(0);
  }, [isGenerating, processStartTime]);

  useEffect(() => {
    logsEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [processLogs]);

  const readSse = async (
    response: Response,
    workflow: WorkflowName,
    onUpdate?: (payload: any) => void
  ) => {
    const reader = response.body?.getReader();
    const decoder = new TextDecoder('utf-8');
    if (!reader) throw new Error('流式读取器初始化失败');

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

        const payload = JSON.parse(dataStr);
        if (payload.thread_id) {
          if (workflow === 'conversational_tone') {
            setScriptThreadContext(payload.thread_id, payload.checkpoint_id ?? undefined);
          } else {
            setAnimationThreadContext(payload.thread_id, payload.checkpoint_id ?? undefined);
          }
        }
        if (payload.type === 'end' && payload.checkpoint_id) {
          if (workflow === 'conversational_tone') {
            setScriptThreadContext(payload.thread_id ?? scriptThreadId, payload.checkpoint_id);
          } else {
            setAnimationThreadContext(
              payload.thread_id ?? animationThreadId,
              payload.checkpoint_id
            );
          }
        }
        onUpdate?.(payload);
      }
    }
  };

  const handleChange = useCallback(
    (val: string | undefined) => {
      if (!activeSceneId) return;
      updateSceneCode(activeSceneId, val ?? '');
    },
    [activeSceneId, updateSceneCode]
  );

  const loadHistory = useCallback(
    async (workflow: WorkflowName) => {
      const threadId = workflow === 'conversational_tone' ? scriptThreadId : animationThreadId;
      if (!threadId) {
        addProcessLog(`当前没有可查询的${workflow === 'conversational_tone' ? '口语稿' : '视频'}历史线程`);
        return;
      }

      setHistoryLoading(true);
      setHistoryWorkflow(workflow);
      try {
        const response = await fetch(
          `/api/workflows/${workflow}/history?thread_id=${encodeURIComponent(threadId)}&limit=12`
        );
        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`);
        }
        const data = await response.json();
        setHistoryItems(data.items ?? []);
        addProcessLog(`已加载 ${workflow === 'conversational_tone' ? '口语稿' : '视频'} 历史检查点`);
      } catch (err) {
        addProcessLog(`加载历史失败: ${(err as Error).message}`);
      } finally {
        setHistoryLoading(false);
      }
    },
    [
      addProcessLog,
      animationThreadId,
      scriptThreadId,
      setHistoryItems,
      setHistoryLoading,
      setHistoryWorkflow,
    ]
  );

  const replayWorkflow = useCallback(
    async (workflow: WorkflowName, checkpointId: string) => {
      const threadId = workflow === 'conversational_tone' ? scriptThreadId : animationThreadId;
      if (!threadId) return;

      clearProcessLogs();
      setProcessStartTime(Date.now());

      if (workflow === 'conversational_tone') {
        setRewriteStatus('generating');
        setAiStatus('idle');
      } else {
        setAiStatus('generating');
        setRewriteStatus('idle');
      }

      addProcessLog(`开始从历史检查点重放${workflow === 'conversational_tone' ? '口语稿' : '视频'}流程...`);

      try {
        const response = await fetch(`/api/workflows/${workflow}/replay_sse`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            thread_id: threadId,
            checkpoint_id: checkpointId,
          }),
        });
        if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);

        await readSse(response, workflow, (payload) => {
          if (payload.type === 'error') {
            throw new Error(payload.message || '历史重放失败');
          }

          if (payload.type === 'updates' && payload.data) {
            let updateData = payload.data;
            if (updateData.type === 'updates' && updateData.data) {
              updateData = updateData.data;
            }

            const nodeName = Object.keys(updateData)[0];
            const nodeData = updateData[nodeName];
            if (!nodeName || !nodeData) return;

            addProcessLog(`[历史重放] ${nodeName} 完成`);

            if (workflow === 'conversational_tone' && nodeData.current_script) {
              setOralScript(nodeData.current_script);
            }

            if (workflow === 'animation') {
              if (nodeName === 'director_node' && nodeData.director?.scenes) {
                const parsedScenes = nodeData.director.scenes.map((scene: any) => ({
                  id: scene.scene_id,
                  durationInFrames: 150,
                  componentType: scene.scene_id.replace(/\s+/g, ''),
                  script: scene.script,
                  marks: scene.animation_marks || {},
                  code:
                    '// 正在等待 Coder Agent 生成代码...\n// 视觉设计要求:\n// ' +
                    scene.visual_design,
                }));
                setScenes(parsedScenes);
              }

              if (nodeName === 'coder_node' && nodeData.coder) {
                const coders = Array.isArray(nodeData.coder) ? nodeData.coder : [nodeData.coder];
                coders.forEach((coder: any) => {
                  updateSceneCode(coder.scene_id, coder.code);
                });
              }
            }
          }
        });

        addProcessLog('历史重放完成');
        if (workflow === 'conversational_tone') {
          setRewriteStatus('success');
        } else {
          setAiStatus('idle');
        }
        setProcessStartTime(null);
      } catch (err) {
        addProcessLog(`历史重放失败: ${(err as Error).message}`);
        if (workflow === 'conversational_tone') {
          setRewriteStatus('error');
        } else {
          setAiStatus('error');
        }
        setProcessStartTime(null);
      }
    },
    [
      addProcessLog,
      animationThreadId,
      clearProcessLogs,
      readSse,
      scriptThreadId,
      setAiStatus,
      setOralScript,
      setProcessStartTime,
      setRewriteStatus,
      setScenes,
      updateSceneCode,
    ]
  );

  const retryRewrite = useCallback(async () => {
    setRewriteStatus('generating');
    setAiStatus('idle');
    clearProcessLogs();
    setProcessStartTime(Date.now());
    addProcessLog('正在重试口语稿生成...');

    try {
      const response = await fetch('/api/generate_script_sse', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ source_text: sourceText, thread_id: scriptThreadId }),
      });
      if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);

      await readSse(response, 'conversational_tone', (payload) => {
        if (payload.type === 'error') throw new Error(payload.message || '口语稿重试失败');
        if (payload.type === 'updates' && payload.data) {
          const updateData = payload.data;
          const nodeName = Object.keys(updateData)[0];
          const nodeData = updateData[nodeName];
          if (!nodeName || !nodeData) return;
          addProcessLog(`[节点运行] ${nodeName} 处理完成`);
          if (nodeData.current_script) {
            setOralScript(nodeData.current_script);
            addProcessLog('[输出] 最新口语稿已生成', nodeData.current_script);
          }
        }
      });

      addProcessLog('口语稿重试成功');
      setRewriteStatus('success');
      setProcessStartTime(null);
    } catch (err) {
      addProcessLog(`口语稿重试失败: ${(err as Error).message}`);
      setRewriteStatus('error');
      setProcessStartTime(null);
    }
  }, [
    addProcessLog,
    clearProcessLogs,
    readSse,
    scriptThreadId,
    setAiStatus,
    setOralScript,
    setProcessStartTime,
    setRewriteStatus,
    sourceText,
  ]);

  const retryVideo = useCallback(async () => {
    setAiStatus('generating');
    setRewriteStatus('idle');
    clearProcessLogs();
    setProcessStartTime(Date.now());
    addProcessLog('正在重试视频生成...');

    try {
      const response = await fetch('/api/generate_animation_sse', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ source_text: oralScript, thread_id: animationThreadId }),
      });
      if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);

      await readSse(response, 'animation', (payload) => {
        if (payload.type === 'error') throw new Error(payload.message || '视频重试失败');
        if (payload.type === 'updates' && payload.data) {
          let updateData = payload.data;
          if (updateData.type === 'updates' && updateData.data) {
            updateData = updateData.data;
          }
          const nodeName = Object.keys(updateData)[0];
          const nodeData = updateData[nodeName];
          if (!nodeName || !nodeData) return;

          addProcessLog(`[视频流程] ${nodeName} 步骤完成`);
          if (nodeName === 'director_node' && nodeData.director?.scenes) {
            const parsedScenes = nodeData.director.scenes.map((scene: any) => ({
              id: scene.scene_id,
              durationInFrames: 150,
              componentType: scene.scene_id.replace(/\s+/g, ''),
              script: scene.script,
              marks: scene.animation_marks || {},
              code:
                '// 正在等待 Coder Agent 生成代码...\n// 视觉设计要求:\n// ' +
                scene.visual_design,
            }));
            setScenes(parsedScenes);
          }
          if (nodeName === 'coder_node' && nodeData.coder) {
            const coders = Array.isArray(nodeData.coder) ? nodeData.coder : [nodeData.coder];
            coders.forEach((coder: any) => {
              updateSceneCode(coder.scene_id, coder.code);
            });
          }
        }
      });

      addProcessLog('视频重试成功');
      setAiStatus('idle');
      setProcessStartTime(null);
    } catch (err) {
      addProcessLog(`视频重试失败: ${(err as Error).message}`);
      setAiStatus('error');
      setProcessStartTime(null);
    }
  }, [
    addProcessLog,
    animationThreadId,
    clearProcessLogs,
    oralScript,
    readSse,
    setAiStatus,
    setProcessStartTime,
    setRewriteStatus,
    setScenes,
    updateSceneCode,
  ]);

  const retryHandler =
    rewriteStatus === 'error' ? retryRewrite : aiStatus === 'error' ? retryVideo : undefined;

  return (
    <div className="w-[42%] flex flex-col bg-[#1e1e1e]">
      <div className="px-4 py-3 border-b border-gray-800 flex items-center justify-between bg-[#18181b] flex-shrink-0">
        <div className="flex items-center gap-2">
          <Code2 className="w-4 h-4 text-blue-400" />
          <span className="text-xs font-semibold text-gray-300">
            {hasScenes ? 'GeneratedScene.tsx' : '代码区待生成'}
          </span>
        </div>
        {isGenerating && activeTask && (
          <span className="text-[11px] text-blue-400 flex items-center gap-1">
            <Loader2 className="w-3 h-3 animate-spin" />
            同步{activeTask}中
          </span>
        )}
      </div>

      <div className="flex-1 min-h-0 border-b border-gray-800">
        {!hasScenes ? (
          <div className="h-full flex items-center justify-center px-6 bg-[#111113]">
            <div className="max-w-[260px] text-center">
              <p className="text-sm text-gray-300">代码编辑区会在分镜生成后开放。</p>
              <p className="mt-2 text-[12px] text-gray-500">未开始前不再展示示例代码，避免打断主流程判断。</p>
            </div>
          </div>
        ) : (
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
        )}
      </div>

      <div className="h-72 bg-[#0e0e11] flex flex-col flex-shrink-0">
        <div className="px-4 py-2 border-b border-gray-800 flex items-center justify-between bg-[#18181b] gap-3">
          <div className="flex items-center gap-2">
            <TerminalSquare className="w-4 h-4 text-green-400" />
            <span className="text-[11px] font-semibold text-gray-400 uppercase tracking-wider">执行日志</span>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={() => loadHistory('conversational_tone')}
              disabled={historyLoading || !scriptThreadId}
              className="text-[11px] flex items-center gap-1 text-gray-300 border border-gray-700 px-2 py-1 rounded disabled:opacity-40 hover:border-gray-500 transition-colors"
            >
              <History className="w-3 h-3" />
              口语稿历史
            </button>
            <button
              onClick={() => loadHistory('animation')}
              disabled={historyLoading || !animationThreadId}
              className="text-[11px] flex items-center gap-1 text-gray-300 border border-gray-700 px-2 py-1 rounded disabled:opacity-40 hover:border-gray-500 transition-colors"
            >
              <History className="w-3 h-3" />
              视频历史
            </button>
          </div>
        </div>

        {historyWorkflow && (
          <div className="border-b border-gray-800 px-3 py-2 bg-[#101014]">
            <div className="flex items-center justify-between mb-2">
              <span className="text-[11px] text-gray-400">
                {historyWorkflow === 'conversational_tone' ? '口语稿' : '视频'}检查点历史
              </span>
              <button
                onClick={() => loadHistory(historyWorkflow)}
                disabled={historyLoading}
                className="text-[11px] text-gray-300 flex items-center gap-1"
              >
                <RefreshCw className={`w-3 h-3 ${historyLoading ? 'animate-spin' : ''}`} />
                刷新
              </button>
            </div>
            <div className="space-y-2 max-h-32 overflow-y-auto">
              {historyItems.length === 0 ? (
                <div className="text-[11px] text-gray-500">暂无历史检查点</div>
              ) : (
                historyItems.map((item) => (
                  <HistoryRow
                    key={item.checkpoint_id}
                    item={item}
                    onReplay={(checkpointId) => replayWorkflow(historyWorkflow, checkpointId)}
                  />
                ))
              )}
            </div>
          </div>
        )}

        <div className="flex-1 overflow-y-auto p-3 text-xs font-mono">
          {processLogs.length === 0 ? (
            <div className="flex flex-col gap-1.5 text-gray-500 mt-1">
              <span className="text-gray-400">从左侧开始流程后，这里会实时显示执行日志。</span>
              <span className="text-gray-600 text-[11px]">日志会覆盖口语稿生成、视频生成和历史重放三个阶段。</span>
            </div>
          ) : (
            processLogs.map((log, i) => {
              const isLastRow = i === processLogs.length - 1;
              return (
                <LogItem
                  key={i}
                  log={log}
                  onRetry={isLastRow && !isGenerating ? retryHandler : undefined}
                />
              );
            })
          )}
          {isGenerating && activeTask && (
            <div className="flex items-center gap-1.5 text-blue-400 mt-1">
              <Loader2 className="w-2.5 h-2.5 animate-spin" />
              <span>{activeTask}处理中... {elapsed}s</span>
            </div>
          )}
          <div ref={logsEndRef} />
        </div>
      </div>
    </div>
  );
};
