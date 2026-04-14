import type { Scene } from '../types/scene';
import type { IdeState } from './useIdeStore';

const EMPTY_SCENE: Scene = {
  id: '',
  sceneArtifactId: null,
  artifactId: null,
  version: 1,
  status: 'draft',
  validationReport: null,
  previewImageUrl: null,
  durationInFrames: 150,
  componentType: 'Scene',
  script: '',
  visual_design: '',
  code: '',
  marks: {},
};

export const selectActiveScene = (state: IdeState): Scene =>
  state.scenes.find((s) => s.id === state.activeSceneId) ?? EMPTY_SCENE;

export const selectTotalFrames = (state: IdeState): number =>
  state.scenes.reduce((sum, s) => sum + s.durationInFrames, 0);

export interface ScriptMetrics {
  charCount: number;
  estimatedSec: number;
  sceneDurationSec: number;
  isTooLong: boolean;
}

export const selectScriptMetrics = (state: IdeState): ScriptMetrics => {
  const scene = selectActiveScene(state);
  const charCount = scene.script.replace(/\s/g, '').length;
  const estimatedSec = charCount / 4;
  const sceneDurationSec = scene.durationInFrames / 30;

  return {
    charCount,
    estimatedSec,
    sceneDurationSec,
    isTooLong: estimatedSec > sceneDurationSec,
  };
};
