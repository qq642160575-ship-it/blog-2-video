import React from 'react';
import { Wand2, Loader2 } from 'lucide-react';
import { useIdeStore } from '../../store/useIdeStore';

/**
 * 博文原文输入区。
 *
 * 修正点：sourceText 真正接入 store，handleRegenerate 能读取到真实内容。
 * 后续对接后端接口时，只需替换 mock 逻辑，数据链路已打通。
 */
export const SourceInput: React.FC = () => {
  const sourceText = useIdeStore((s) => s.sourceText);
  const setSourceText = useIdeStore((s) => s.setSourceText);
  const aiStatus = useIdeStore((s) => s.aiStatus);
  const setAiStatus = useIdeStore((s) => s.setAiStatus);

  const isGenerating = aiStatus === 'generating';

  const handleRegenerate = async () => {
    setAiStatus('generating');
    try {
      // TODO: 替换为真实后端接口调用，入参为 sourceText
      // const result = await api.generateScenes(sourceText);
      // useIdeStore.getState().setScenes(result.scenes);
      await new Promise((resolve) => setTimeout(resolve, 2000));
      setAiStatus('idle');
    } catch (err) {
      console.error('生成失败:', err);
      setAiStatus('error');
    }
  };

  return (
    <div>
      <div className="flex justify-between items-center mb-2">
        <h3 className="text-[10px] text-gray-500 font-bold uppercase tracking-wider">
          Source 博文原文
        </h3>
        <button
          onClick={handleRegenerate}
          disabled={isGenerating}
          className="text-[10px] text-purple-400 hover:text-purple-300 flex items-center gap-1 disabled:opacity-50 transition-colors"
        >
          {isGenerating ? (
            <Loader2 className="w-3 h-3 animate-spin" />
          ) : (
            <Wand2 className="w-3 h-3" />
          )}
          重新生成
        </button>
      </div>
      <textarea
        value={sourceText}
        onChange={(e) => setSourceText(e.target.value)}
        className="w-full text-xs text-gray-300 bg-[#0e0e11] p-2.5 rounded border border-gray-800 focus:border-purple-500/50 focus:outline-none resize-none h-24"
      />
    </div>
  );
};
