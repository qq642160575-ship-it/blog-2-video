import { useIdeStore } from '../store/useIdeStore';
import { selectActiveScene } from '../store/selectors';
import type { ScriptMetrics } from '../store/selectors';

/**
 * 封装当前激活场景的文案指标：字数、预估时长、片段时长、是否超时。
 *
 * 修复：不能把返回对象的 selector 直接传给 useIdeStore()。
 * Zustand 用 Object.is 比较 snapshot，每次调用都是新对象引用
 * → 无限触发 forceStoreRerender → Maximum update depth exceeded。
 *
 * 解决：分开订阅各个标量字段，Object.is 对基本类型按值比较，不会误判变化。
 */
export function useScriptMetrics(): ScriptMetrics {
  const script = useIdeStore((s) => selectActiveScene(s).script);
  const durationInFrames = useIdeStore((s) => selectActiveScene(s).durationInFrames);

  const charCount = script.replace(/\s/g, '').length;
  const estimatedSec = charCount / 4; // 中文约 4 字/秒
  const sceneDurationSec = durationInFrames / 30;

  return {
    charCount,
    estimatedSec,
    sceneDurationSec,
    isTooLong: estimatedSec > sceneDurationSec,
  };
}
