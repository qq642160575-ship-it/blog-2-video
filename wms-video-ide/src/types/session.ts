export interface UserPreference {
  style_family?: string | null;
  duration_seconds?: number | null;
}

export interface CreateSessionRequest {
  source_type: string;
  source_content: string;
  title?: string | null;
  user_preference?: UserPreference | null;
}

export interface CreateSessionResponse {
  session_id: string;
  branch_id: string;
  status: string;
}

export interface SessionOverview {
  session_id: string;
  title: string | null;
  source_type: string;
  status: string;
  current_branch_id: string | null;
}
