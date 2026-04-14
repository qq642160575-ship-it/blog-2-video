export type SceneSpec = {
  scene_id: string;
  type: string;
  start: number;
  end: number;
  duration_in_frames: number;
  text: string;
  narrative_role: string;
  visual_goal: string;
  layout_slots: string[];
  motion_profile: string;
  priority: number;
};

export type MarksSpec = {
  fps: number;
  duration_in_frames: number;
  global_marks: Record<string, number>;
  scene_marks: Record<string, Record<string, number>>;
};

// Replace generic types with detailed specs based on backend outputs
export type LayoutSpec = Record<string, any>;
export type MotionSpec = Record<string, any>;
export type DslSpec = Record<string, any>;
export type SceneCodeSpec = {
  scene_id: string;
  code: string;
  component_name?: string;
};

export type ValidationErrorItem = {
  code: string;
  message?: string;
  scene_id?: string;
  node_id?: string;
  stage?: string;
};

export type ValidationSpec = {
  scene_id: string;
  status: 'pass' | 'fail' | 'warning';
  stage: string;
  repairable: boolean;
  errors: ValidationErrorItem[];
};
