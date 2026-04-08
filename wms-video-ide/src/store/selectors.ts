import type { Scene } from '../types/scene';
import type { IdeState } from './useIdeStore';

// ── 基础派生 ──

export const selectActiveScene = (state: IdeState): Scene =>
  state.scenes.find((s) => s.id === state.activeSceneId) ?? state.scenes[0];

export const selectTotalFrames = (state: IdeState): number =>
  state.scenes.reduce((sum, s) => sum + s.durationInFrames, 0);

// ── 文案指标 ──

export interface ScriptMetrics {
  charCount: number;
  estimatedSec: number;
  sceneDurationSec: number;
  isTooLong: boolean;
}

export const selectScriptMetrics = (state: IdeState): ScriptMetrics => {
  const scene = selectActiveScene(state);
  const charCount = scene.script.replace(/\s/g, '').length;
  const estimatedSec = charCount / 4; // 中文约 4 字/秒
  const sceneDurationSec = scene.durationInFrames / 30;
  return {
    charCount,
    estimatedSec,
    sceneDurationSec,
    isTooLong: estimatedSec > sceneDurationSec,
  };
};
