import { fetchJson, postJson } from './client';
import type { CreateSessionRequest, CreateSessionResponse, SessionOverview } from '../types/session';
import type { CreateTaskRequest, CreateTaskResponse } from '../types/task';
import type { SessionTimelineResponse } from '../types/event';

export const createSession = (payload: CreateSessionRequest) =>
  postJson<CreateSessionResponse>('/api/sessions', payload);

export const getSession = (sessionId: string) =>
  fetchJson<SessionOverview>(`/api/sessions/${encodeURIComponent(sessionId)}`);

export const getSessionTimeline = (sessionId: string, branchId?: string | null, limit = 100) => {
  const params = new URLSearchParams({ limit: String(limit) });
  if (branchId) params.set('branch_id', branchId);
  return fetchJson<SessionTimelineResponse>(
    `/api/sessions/${encodeURIComponent(sessionId)}/timeline?${params.toString()}`
  );
};

export const createSessionTask = (sessionId: string, payload: CreateTaskRequest) =>
  postJson<CreateTaskResponse>(`/api/sessions/${encodeURIComponent(sessionId)}/tasks`, payload);
