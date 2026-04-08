export interface Scene {
  id: string;
  durationInFrames: number;
  componentType: string;
  script: string;
  code: string;
  marks: Record<string, number>;
}
