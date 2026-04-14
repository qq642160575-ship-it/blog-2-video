export type TaskType =
  | 'create_video'
  | 'regenerate_scene'
  | 'repair_scene'
  | 'render_preview';

export type TaskStatus =
  | 'pending'
  | 'queued'
  | 'running'
  | 'succeeded'
  | 'failed'
  | 'cancelled'
  | 'retrying'
  | 'blocked';

export interface CreateTaskRequest {
  branch_id: string;
  task_type: TaskType;
  request_payload: Record<string, unknown>;
  baseline_artifact_id?: string | null;
}

export interface CreateTaskResponse {
  task_id: string;
  status: TaskStatus;
}

export interface TaskRecord {
  id: string;
  session_id: string;
  branch_id: string;
  task_type: TaskType;
  status: TaskStatus;
  priority: number;
  requested_by?: string | null;
  request_payload: Record<string, unknown>;
  baseline_artifact_id?: string | null;
  result_summary: Record<string, unknown>;
  error_code?: string | null;
  error_message?: string | null;
  cancellation_requested: boolean;
  created_at: string;
  started_at?: string | null;
  finished_at?: string | null;
}
