export type PipelineStage =
  | 'idle'
  | 'script_generating'
  | 'script_ready'
  | 'animation_generating'
  | 'partial_success'
  | 'success'
  | 'error';

export type PipelineError = {
  type: 'compile' | 'agent' | 'render' | 'network';
  stage?: string;
  scene_id?: string;
  code?: string;
  message: string;
  repairable?: boolean;
};

export type ScriptSegment = {
  segment_id: string;
  text: string;
  role: string;
  importance: number;
};

export type ParsedScript = {
  source_id: string;
  intent: string;
  tone: string;
  emotion_curve: string[];
  segments: ScriptSegment[];
};
