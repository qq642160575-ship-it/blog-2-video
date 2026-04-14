import { useCallback } from 'react';
import { listTaskEvents, openTaskEventsSse } from '../api/tasks';
import { readSse } from '../utils/sse';
import type { TaskEventRecord } from '../types/event';

interface StreamTaskOptions {
  onEvent: (event: TaskEventRecord) => void;
}

export const useTaskSse = () => {
  return useCallback(async (taskId: string, options: StreamTaskOptions) => {
    const seen = new Set<string>();
    const initial = await listTaskEvents(taskId);
    initial.items.forEach((event) => {
      seen.add(event.id);
      options.onEvent(event);
    });

    const response = await openTaskEventsSse(taskId);
    await readSse(response, (payload) => {
      const event = payload as TaskEventRecord;
      if (!event?.id || seen.has(event.id)) return;
      seen.add(event.id);
      options.onEvent(event);
    });
  }, []);
};
