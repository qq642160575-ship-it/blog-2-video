import type { Scene } from '../types/scene';

type DirectorScenePayload = {
  scene_id: string;
  duration?: number;
  script?: string;
  visual_design?: string;
  animation_marks?: Record<string, number>;
};

type CoderPayload = {
  scene_id: string;
  code?: string;
};

export const toScenesFromDirectorNode = (
  scenes: DirectorScenePayload[] | undefined,
  placeholderPrefix = '// 正在等待 Coder Agent 生成代码...'
): Scene[] => {
  if (!Array.isArray(scenes)) return [];
  return scenes.map((scene) => ({
    id: scene.scene_id,
    sceneArtifactId: null,
    artifactId: null,
    version: 1,
    status: 'draft',
    validationReport: null,
    previewImageUrl: null,
    durationInFrames: Math.ceil((scene.duration || 5) * 30),
    componentType: scene.scene_id.replace(/\s+/g, ''),
    script: scene.script || '',
    visual_design: scene.visual_design || '',
    code: `${placeholderPrefix}\n// 视觉设计要求：\n// ${scene.visual_design || ''}`,
    marks: scene.animation_marks || {},
  }));
};

export const getCoderUpdates = (payload: unknown): CoderPayload[] => {
  if (!payload) return [];
  return Array.isArray(payload) ? (payload as CoderPayload[]) : [payload as CoderPayload];
};
