import React, { useState, useEffect } from 'react';
import { Loader2, Sparkles, Video, ChevronDown, ChevronUp, CheckCircle2 } from 'lucide-react';
import { useIdeStore } from '../../store/useIdeStore';

/**
 * 博文原文输入 & 口语化处理区
 */
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

  const isGeneratingVideo = aiStatus === 'generating';
  const isRewriting = rewriteStatus === 'generating';

  // 用于折叠面板的状态管理
  const [step1Open, setStep1Open] = useState(true);
  const [step2Open, setStep2Open] = useState(false);

  // 当生成口语文案结束后，自动折叠博文区，展开文案区
  useEffect(() => {
    if (rewriteStatus === 'success' && oralScript) {
      setStep1Open(false);
      setStep2Open(true);
    }
  }, [rewriteStatus, oralScript]);

  const handleRewrite = async () => {
    setRewriteStatus('generating');
    clearProcessLogs();
    setProcessStartTime(Date.now());
    addProcessLog('🚀 开始连接到服务端生成流程...');
    try {
      const response = await fetch('/api/generate_script_sse', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ source_text: sourceText }),
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const reader = response.body?.getReader();
      const decoder = new TextDecoder('utf-8');
      
      if (!reader) throw new Error('流式读取器初始化失败');

      let currentScript = '';
      let buffer = '';

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;
        
        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        
        // Keep the last incomplete line in the buffer
        buffer = lines.pop() || '';
        
        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const dataStr = line.replace('data: ', '').trim();
            if (!dataStr) continue;
            
            try {
              const data = JSON.parse(dataStr);
              if (data.type === 'setup' || data.type === 'end') {
                addProcessLog(`[${data.type.toUpperCase()}] ${data.message}`);
              } else if (data.type === 'updates' && data.data) {
                const updateData = data.data;
                const nodeName = Object.keys(updateData)[0];
                const nodeData = updateData[nodeName];
                
                if (nodeName && nodeData) {
                  addProcessLog(`[节点运行] ⚡ ${nodeName} 处理完毕`);
                  if (nodeData.script) {
                      currentScript = nodeData.script;
                      setOralScript(currentScript);
                      addProcessLog(`[产出] 最新文案已生成`, currentScript);
                  }
                  if (nodeData.loop_details && nodeData.loop_details.length > 0) {
                      const latest = nodeData.loop_details[nodeData.loop_details.length - 1];
                      addProcessLog(`[评估] 第 ${latest.loop_count} 轮得分: ${latest.current_score}`);
                      if (latest.feedback) {
                          addProcessLog(`[反馈] 评估详细内容`, latest.feedback);
                      }
                  }
                }
              }
            } catch (e) {
              console.warn('解析 SSE data 失败:', dataStr, e);
            }
          }
        }
      }
      
      addProcessLog('✅ 流程结束，生成完毕！');
      setRewriteStatus('success');
      setProcessStartTime(null);
    } catch (err) {
      console.error('口语化转化失败:', err);
      addProcessLog('❌ 生成出错：' + (err as Error).message);
      setRewriteStatus('error');
      setProcessStartTime(null);
    }
  };

  const handleGenerateVideo = async () => {
    setAiStatus('generating');
    try {
      // TODO: Call backend Director -> Architect -> Coder with oralScript
      await new Promise((resolve) => setTimeout(resolve, 2000));
      setAiStatus('idle');
      // 可以顺势折叠步骤 2 以留出屏幕空间
      setStep2Open(false);
    } catch (err) {
      console.error('生成视频失败:', err);
      setAiStatus('error');
    }
  };

  return (
    <div className="flex flex-col gap-4">
      {/* 步骤 1：录入原文 */}
      <div className="border border-gray-800 rounded-lg overflow-hidden flex-shrink-0 bg-[#141416]">
        <button
          onClick={() => setStep1Open(!step1Open)}
          className="w-full flex items-center justify-between px-4 py-3 bg-[#1c1c1f] hover:bg-[#232326] transition-colors"
        >
          <div className="flex items-center gap-2">
            <span className="flex items-center justify-center w-5 h-5 rounded-full bg-blue-500/10 text-blue-400 text-[10px] font-bold">1</span>
            <h3 className="text-xs text-gray-300 font-bold tracking-wide">原始技术博文</h3>
          </div>
          <div className="flex items-center gap-3">
            {oralScript && !step1Open && <CheckCircle2 className="w-3.5 h-3.5 text-green-500" />}
            {step1Open ? <ChevronUp className="w-4 h-4 text-gray-500" /> : <ChevronDown className="w-4 h-4 text-gray-500" />}
          </div>
        </button>
        {step1Open && (
          <div className="p-3 border-t border-gray-800 flex flex-col gap-3">
            <textarea
              value={sourceText}
              onChange={(e) => setSourceText(e.target.value)}
              placeholder="在此输入您的原始发稿材料或技术博文..."
              className="w-full text-sm text-gray-300 bg-[#0a0a0c] p-3 rounded-md border border-gray-800 focus:border-blue-500/50 focus:outline-none resize-none leading-relaxed transition-colors"
              rows={8}
            />
            <div className="flex justify-end">
              <button
                onClick={handleRewrite}
                disabled={isRewriting || !sourceText}
                className="text-xs text-white font-semibold flex items-center gap-1.5 disabled:opacity-50 transition-all bg-blue-600 hover:bg-blue-500 px-4 py-2 rounded shadow hover:shadow-lg hover:-translate-y-0.5 active:translate-y-0"
              >
                {isRewriting ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Sparkles className="w-3.5 h-3.5" />}
                {isRewriting ? '正在生成智能口语化文案...' : '转化为口语文案'}
              </button>
            </div>
          </div>
        )}
      </div>

      {/* 步骤 2：生成的口语脚本 */}
      {(oralScript || isRewriting) && (
        <div className="border border-gray-800 rounded-lg overflow-hidden flex-shrink-0 bg-[#141416]">
          <button
            onClick={() => setStep2Open(!step2Open)}
            className="w-full flex items-center justify-between px-4 py-3 bg-[#1c1c1f] hover:bg-[#232326] transition-colors"
          >
            <div className="flex items-center gap-2">
              <span className="flex items-center justify-center w-5 h-5 rounded-full bg-purple-500/10 text-purple-400 text-[10px] font-bold">2</span>
              <h3 className="text-xs text-gray-300 font-bold tracking-wide">视频口语化脚本</h3>
            </div>
            {step2Open ? <ChevronUp className="w-4 h-4 text-gray-500" /> : <ChevronDown className="w-4 h-4 text-gray-500" />}
          </button>
          
          {step2Open && (
            <div className="p-3 border-t border-gray-800 flex flex-col gap-3">
              <textarea
                value={oralScript}
                onChange={(e) => setOralScript(e.target.value)}
                disabled={isRewriting}
                placeholder="生成的初稿内容会落在这里，您可以人工微调润色..."
                className={`w-full text-sm bg-[#0a0a0c] p-3 rounded-md border ${isRewriting ? 'alert-pulse border-blue-500/50 text-gray-500' : 'border-gray-800 text-yellow-100 focus:border-purple-500/50'} focus:outline-none resize-none leading-relaxed transition-all`}
                rows={8}
              />
              <div className="flex justify-end">
                <button
                  onClick={handleGenerateVideo}
                  disabled={isGeneratingVideo || isRewriting || !oralScript}
                  className="text-xs text-white font-semibold flex items-center gap-1.5 disabled:opacity-50 transition-all bg-purple-600 hover:bg-purple-500 px-4 py-2 rounded shadow hover:shadow-lg hover:-translate-y-0.5 active:translate-y-0"
                >
                  {isGeneratingVideo ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Video className="w-3.5 h-3.5" />}
                  {isGeneratingVideo ? '正在编排多智能体...' : '导入 Timeline 并生成视频分镜'}
                </button>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

