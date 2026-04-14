export interface TaskEventRecord {
  id: string;
  task_id: string;
  task_run_id?: string | null;
  session_id: string;
  branch_id: string;
  scene_id?: string | null;
  event_type: string;
  event_level: string;
  node_key?: string | null;
  payload: Record<string, unknown>;
  created_at: string;
}

export interface TaskEventsResponse {
  items: TaskEventRecord[];
}

export interface SessionTimelineResponse {
  items: TaskEventRecord[];
}
