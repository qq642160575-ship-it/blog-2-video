import { useIdeStore } from '../store/useIdeStore';
import { useShallow } from 'zustand/react/shallow';
import { selectScriptMetrics } from '../store/selectors';
import type { ScriptMetrics } from '../store/selectors';

/**
 * 封装当前激活场景的文案指标：字数、预估时长、片段时长、是否超时。
 *
 * 使用 useShallow 浅比较解决 selectScriptMetrics 每次返回新对象引用
 * 导致 Object.is 误判变化、触发无限重渲染的问题。
 * 计算逻辑统一在 selectors.ts 维护，符合单一真相原则。
 */
export function useScriptMetrics(): ScriptMetrics {
  return useIdeStore(useShallow(selectScriptMetrics));
}
