import React from 'react';
import { Loader2, Sparkles, Video } from 'lucide-react';
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

  const isGeneratingVideo = aiStatus === 'generating';
  const isRewriting = rewriteStatus === 'generating';

  const handleRewrite = async () => {
    setRewriteStatus('generating');
    try {
      // TODO: Call backend /api/rewrite to use content_writer loop
      await new Promise((resolve) => setTimeout(resolve, 2000));
      setOralScript('大家注意了！WMS 系统的入库单流转非常关键。从 CREATED 到 ARRIVED，中间必须加库存掩码来防止并发错误，否则仓库真的会炸锅！');
      setRewriteStatus('success');
    } catch (err) {
      console.error('口语化转化失败:', err);
      setRewriteStatus('error');
    }
  };

  const handleGenerateVideo = async () => {
    setAiStatus('generating');
    try {
      // TODO: Call backend Director -> Architect -> Coder with oralScript
      await new Promise((resolve) => setTimeout(resolve, 2000));
      setAiStatus('idle');
    } catch (err) {
      console.error('生成视频失败:', err);
      setAiStatus('error');
    }
  };

  return (
    <div className="flex flex-col gap-4">
      {/* 步骤 1：录入原文 */}
      <div>
        <div className="flex justify-between items-center mb-2">
          <h3 className="text-[10px] text-gray-500 font-bold uppercase tracking-wider">
            1. 原始技术博文
          </h3>
          <button
            onClick={handleRewrite}
            disabled={isRewriting || !sourceText}
            className="text-[10px] text-blue-400 hover:text-blue-300 flex items-center gap-1 disabled:opacity-50 transition-colors bg-blue-500/10 px-2 py-1 rounded"
          >
            {isRewriting ? <Loader2 className="w-3 h-3 animate-spin" /> : <Sparkles className="w-3 h-3" />}
            转化为口语文案
          </button>
        </div>
        <textarea
          value={sourceText}
          onChange={(e) => setSourceText(e.target.value)}
          placeholder="在此输入您的技术博文..."
          className="w-full text-xs text-gray-300 bg-[#0e0e11] p-2.5 rounded border border-gray-800 focus:border-blue-500/50 focus:outline-none resize-none h-20"
        />
      </div>

      {/* 步骤 2：生成的口语脚本 */}
      {(oralScript || isRewriting) && (
        <div className="pt-2 border-t border-gray-800 border-dashed">
          <div className="flex justify-between items-center mb-2">
            <h3 className="text-[10px] text-gray-500 font-bold uppercase tracking-wider">
              2. 视频口语化脚本 (可微调)
            </h3>
            <button
              onClick={handleGenerateVideo}
              disabled={isGeneratingVideo || isRewriting || !oralScript}
              className="text-[10px] text-purple-400 hover:text-purple-300 flex items-center gap-1 disabled:opacity-50 transition-colors bg-purple-500/10 px-2 py-1 rounded shadow"
            >
              {isGeneratingVideo ? <Loader2 className="w-3 h-3 animate-spin" /> : <Video className="w-3 h-3" />}
              基于此脚本生成视频
            </button>
          </div>
          <textarea
            value={oralScript}
            onChange={(e) => setOralScript(e.target.value)}
            disabled={isRewriting}
            className={`w-full text-xs bg-[#0e0e11] p-2.5 rounded border ${isRewriting ? 'alert-pulse border-blue-500/50 text-gray-500' : 'border-gray-800 text-yellow-100 focus:border-purple-500/50'} focus:outline-none resize-none h-24`}
          />
        </div>
      )}
    </div>
  );
};

