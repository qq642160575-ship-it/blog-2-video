export interface ArtifactResponse {
  artifact_id: string;
  session_id: string;
  branch_id: string;
  task_id: string | null;
  artifact_type: string;
  artifact_subtype: string | null;
  version: number;
  content_json: Record<string, unknown> | null;
  content_text: string | null;
  storage_url: string | null;
  summary: string | null;
  parent_artifact_id: string | null;
}

export interface SceneArtifactResponse {
  scene_artifact_id: string;
  artifact_id: string;
  session_id: string;
  branch_id: string;
  scene_id: string;
  scene_order: number;
  scene_type: string | null;
  script_text: string | null;
  visual_intent: Record<string, unknown> | null;
  layout_spec: Record<string, unknown> | null;
  code_text: string | null;
  validation_report: Record<string, unknown> | null;
  preview_image_url: string | null;
  status: string;
  version: number;
}

export interface BranchResponse {
  branch_id: string;
  session_id: string;
  parent_branch_id: string | null;
  base_artifact_id: string | null;
  head_artifact_id: string | null;
  version: number;
}
