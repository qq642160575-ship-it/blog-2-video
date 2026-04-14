export interface Scene {
  id: string;
  sceneArtifactId?: string | null;
  artifactId?: string | null;
  version?: number;
  status?: string;
  validationReport?: Record<string, unknown> | null;
  previewImageUrl?: string | null;
  durationInFrames: number;
  componentType: string;
  script: string;
  visual_design: string;
  code: string;
  marks: Record<string, number>;
  layout_spec?: any;
  visual_intent?: any;
}
