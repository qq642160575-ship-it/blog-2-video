import React, { useState } from 'react';
import { Loader2, Sparkles, Video, ChevronDown, ChevronUp, CheckCircle2 } from 'lucide-react';
import { useIdeStore } from '../../store/useIdeStore';

type SsePayload = {
  type: string;
  message?: string;
  data?: Record<string, any>;
  thread_id?: string;
  checkpoint_id?: string | null;
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
  const scriptThreadId = useIdeStore((s) => s.scriptThreadId);
  const animationThreadId = useIdeStore((s) => s.animationThreadId);
  const setScriptThreadContext = useIdeStore((s) => s.setScriptThreadContext);
  const setAnimationThreadContext = useIdeStore((s) => s.setAnimationThreadContext);

  const [step1Open, setStep1Open] = useState(true);
  const [step2Open, setStep2Open] = useState(true);

  const isGeneratingVideo = aiStatus === 'generating';
  const isRewriting = rewriteStatus === 'generating';
  const sourceSummary = `${sourceText.trim().replace(/\s+/g, '').length} 字`;
  const oralSummary = oralScript
    ? `${oralScript.trim().replace(/\s+/g, '').length} 字`
    : '未生成';

  const readSse = async (
    response: Response,
    onPayload: (payload: SsePayload) => void
  ) => {
    const reader = response.body?.getReader();
    const decoder = new TextDecoder('utf-8');

    if (!reader) {
      throw new Error('流式读取器初始化失败');
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
        } catch (e) {
          console.warn('解析 SSE 数据失败:', dataStr, e);
        }
      }
    }
  };

  const handleRewrite = async () => {
    setRewriteStatus('generating');
    setAiStatus('idle');
    clearProcessLogs();
    setProcessStartTime(Date.now());
    addProcessLog('正在连接服务，开始生成口语稿...');

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

        if (payload.type === 'setup' || payload.type === 'end') {
          if (payload.type === 'end' && payload.checkpoint_id) {
            setScriptThreadContext(payload.thread_id ?? scriptThreadId, payload.checkpoint_id);
          }
          addProcessLog(
            payload.type === 'setup' ? '已建立口语稿工作流会话' : '口语稿工作流结束'
          );
          return;
        }

        if (payload.type === 'error') {
          throw new Error(payload.message || '口语稿生成失败');
        }

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

          if (nodeData.review_score !== undefined) {
            addProcessLog(
              `[评估] 当前得分 ${nodeData.review_score}`,
              nodeData.last_feedback || undefined
            );
          }
        }
      });

      addProcessLog('口语稿生成完成');
      setRewriteStatus('success');
      setProcessStartTime(null);
    } catch (err) {
      console.error('口语稿生成失败:', err);
      addProcessLog(`生成出错: ${(err as Error).message}`);
      setRewriteStatus('error');
      setProcessStartTime(null);
    }
  };

  const handleGenerateVideo = async () => {
    setAiStatus('generating');
    setRewriteStatus('idle');
    clearProcessLogs();
    setProcessStartTime(Date.now());
    addProcessLog('启动多智能体视频生成流程...');

    try {
      const response = await fetch('/api/generate_animation_sse', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          source_text: oralScript,
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

        if (payload.type === 'setup' || payload.type === 'end') {
          if (payload.type === 'end' && payload.checkpoint_id) {
            setAnimationThreadContext(
              payload.thread_id ?? animationThreadId,
              payload.checkpoint_id
            );
          }
          addProcessLog(
            payload.type === 'setup' ? '已建立视频工作流会话' : '视频工作流结束'
          );
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
            addProcessLog(`[Director] 已生成 ${parsedScenes.length} 个分镜`);
          }

          if (nodeName === 'visual_architect_node' && nodeData.visual_architect) {
            addProcessLog(
              '[Visual Architect] 主题配置已完成',
              JSON.stringify(nodeData.visual_architect.theme_colors)
            );
          }

          if (nodeName === 'coder_node' && nodeData.coder) {
            const coders = Array.isArray(nodeData.coder) ? nodeData.coder : [nodeData.coder];
            coders.forEach((coder: any) => {
              updateSceneCode(coder.scene_id, coder.code);
              addProcessLog(`[Coder] ${coder.scene_id} 代码已回传`);
            });
          }
        }
      });

      setAiStatus('idle');
      addProcessLog('视频生成流程已完成');
      setProcessStartTime(null);
    } catch (err) {
      console.error('视频生成失败:', err);
      addProcessLog(`视频生成失败: ${(err as Error).message}`);
      setAiStatus('error');
      setProcessStartTime(null);
    }
  };

  return (
    <div className="flex flex-col gap-4">
      <div className="border border-gray-800 rounded-lg overflow-hidden flex-shrink-0 bg-[#141416]">
        <button
          onClick={() => setStep1Open((v) => !v)}
          className="w-full flex items-center justify-between px-4 py-3 bg-[#1c1c1f] hover:bg-[#232326] transition-colors"
        >
          <div className="flex items-center gap-2">
            <span className="flex items-center justify-center w-5 h-5 rounded-full bg-blue-500/10 text-blue-400 text-[10px] font-bold">1</span>
            <h3 className="text-xs text-gray-300 font-bold tracking-wide">原始技术博客</h3>
          </div>
          <div className="flex items-center gap-3">
            {!step1Open && <span className="text-[11px] text-gray-500 font-mono">{sourceSummary}</span>}
            {oralScript && <CheckCircle2 className="w-3.5 h-3.5 text-green-500" />}
            {step1Open ? <ChevronUp className="w-4 h-4 text-gray-500" /> : <ChevronDown className="w-4 h-4 text-gray-500" />}
          </div>
        </button>

        <div
          className={`border-t border-gray-800 transition-all duration-300 overflow-hidden ${
            step1Open ? 'max-h-96 opacity-100' : 'max-h-0 opacity-0'
          }`}
        >
          <div className="p-3 flex flex-col gap-3 relative">
            <textarea
              value={sourceText}
              onChange={(e) => setSourceText(e.target.value)}
              disabled={isRewriting}
              placeholder="在此输入原始技术博客、文章草稿或待改写内容..."
              className={`w-full text-sm text-gray-300 bg-[#0a0a0c] p-3 rounded-md border border-gray-800 focus:border-blue-500/50 focus:outline-none resize-none leading-relaxed transition-all ${
                isRewriting ? 'opacity-40 cursor-not-allowed' : ''
              }`}
              rows={8}
            />
            {isRewriting && (
              <div className="absolute inset-3 rounded-md flex items-center justify-center bg-transparent cursor-not-allowed pointer-events-auto" />
            )}
            <div className="flex items-center justify-between gap-3">
              <span className="text-[12px] text-gray-500">先生成口语稿，再进入分镜与代码阶段</span>
              <button
                onClick={handleRewrite}
                disabled={isRewriting || !sourceText}
                className="text-sm text-white font-semibold flex items-center gap-1.5 disabled:opacity-50 transition-all bg-blue-600 hover:bg-blue-500 px-4 py-2.5 rounded shadow hover:shadow-lg hover:-translate-y-0.5 active:translate-y-0"
              >
                {isRewriting ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Sparkles className="w-3.5 h-3.5" />}
                {isRewriting ? '正在生成口语稿...' : '转化为口语文案'}
              </button>
            </div>
          </div>
        </div>
      </div>

      <div className="border border-gray-800 rounded-lg overflow-hidden flex-shrink-0 bg-[#141416]">
        <button
          onClick={() => setStep2Open((v) => !v)}
          className="w-full flex items-center justify-between px-4 py-3 bg-[#1c1c1f] hover:bg-[#232326] transition-colors"
        >
          <div className="flex items-center gap-2">
            <span className="flex items-center justify-center w-5 h-5 rounded-full bg-purple-500/10 text-purple-400 text-[10px] font-bold">2</span>
            <h3 className="text-xs text-gray-300 font-bold tracking-wide">视频口语化脚本</h3>
          </div>
          <div className="flex items-center gap-3">
            {!step2Open && <span className="text-[11px] text-gray-500 font-mono">{oralSummary}</span>}
            {oralScript && <CheckCircle2 className="w-3.5 h-3.5 text-green-500" />}
            {step2Open ? <ChevronUp className="w-4 h-4 text-gray-500" /> : <ChevronDown className="w-4 h-4 text-gray-500" />}
          </div>
        </button>

        <div
          className={`border-t border-gray-800 transition-all duration-300 overflow-hidden ${
            step2Open ? 'max-h-96 opacity-100' : 'max-h-0 opacity-0'
          }`}
        >
          <div className="p-3 flex flex-col gap-3">
            {isRewriting && !oralScript ? (
              <div className="w-full bg-[#0a0a0c] rounded-md border border-gray-800 p-3" style={{ minHeight: '12rem' }}>
                <div className="space-y-2">
                  {[100, 80, 90, 60, 75].map((w, i) => (
                    <div
                      key={i}
                      className="h-3 bg-gray-800 rounded animate-pulse"
                      style={{ width: `${w}%`, animationDelay: `${i * 100}ms` }}
                    />
                  ))}
                </div>
              </div>
            ) : (
              <textarea
                value={oralScript}
                onChange={(e) => setOralScript(e.target.value)}
                disabled={isRewriting}
                placeholder="生成的口语稿会显示在这里，你也可以手动修改后再继续..."
                className={`w-full text-sm bg-[#0a0a0c] p-3 rounded-md border ${
                  isRewriting
                    ? 'alert-pulse border-blue-500/50 text-gray-500'
                    : 'border-gray-800 text-yellow-100 focus:border-purple-500/50'
                } focus:outline-none resize-none leading-relaxed transition-all`}
                rows={8}
              />
            )}
            <div className="flex items-center justify-between gap-3">
              <span className="text-[12px] text-gray-500">
                {isGeneratingVideo ? '系统正在生成分镜、预览和代码' : '确认口语稿后再导入 Timeline'}
              </span>
              <button
                onClick={handleGenerateVideo}
                disabled={isGeneratingVideo || isRewriting || !oralScript}
                className="text-sm text-white font-semibold flex items-center gap-1.5 disabled:opacity-50 transition-all bg-purple-600 hover:bg-purple-500 px-4 py-2.5 rounded shadow hover:shadow-lg hover:-translate-y-0.5 active:translate-y-0"
              >
                {isGeneratingVideo ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Video className="w-3.5 h-3.5" />}
                {isGeneratingVideo ? '正在编排多智能体...' : '导入 Timeline 并生成视频'}
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
