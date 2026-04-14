import { ensureOk, fetchJson, postJson } from './client';
import type { TaskEventsResponse, TaskEventRecord } from '../types/event';
import type { TaskRecord } from '../types/task';

export const getTask = (taskId: string) =>
  fetchJson<TaskRecord>(`/api/tasks/${encodeURIComponent(taskId)}`);

export const listTaskEvents = (taskId: string) =>
  fetchJson<TaskEventsResponse>(`/api/tasks/${encodeURIComponent(taskId)}/events`);

export const openTaskEventsSse = async (taskId: string): Promise<Response> => {
  const response = await fetch(`/api/tasks/${encodeURIComponent(taskId)}/events_sse`);
  return ensureOk(response);
};

export const cancelTask = (taskId: string) =>
  postJson<{ task_id: string; status: string; cancellation_requested: boolean }>(
    `/api/tasks/${encodeURIComponent(taskId)}/cancel`,
    {}
  );

export const retryTask = (taskId: string) =>
  postJson<{ task_id: string; status: string }>(
    `/api/tasks/${encodeURIComponent(taskId)}/retry`,
    {}
  );

export type { TaskEventRecord };
