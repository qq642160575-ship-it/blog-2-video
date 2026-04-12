export interface Scene {
  id: string;
  durationInFrames: number;
  componentType: string;
  script: string;
  visual_design: string;
  code: string;
  marks: Record<string, number>;
}
