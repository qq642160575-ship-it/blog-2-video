import type { TaskEventRecord } from '../types/event';
import type { WorkflowName } from '../types/workflow';
import type { WorkflowProgress } from '../utils/workflowUi';
import { getNodePresentation } from '../utils/workflowUi';

export interface TaskProgressPatch {
  workflow: WorkflowName;
  patch: Partial<WorkflowProgress>;
}

const formatEventType = (eventType: string) =>
  eventType
    .replace('task.', '任务 ')
    .replace('workflow.', '流程 ')
    .replace('validation.', '校验 ');

export const toProgressPatch = (
  event: TaskEventRecord,
  workflow: WorkflowName
): TaskProgressPatch | null => {
  if (event.event_type === 'task.started') {
    return {
      workflow,
      patch: {
        status: 'running',
        nodeKey: 'director_node',
        nodeLabel: '任务已开始',
        description: '任务已开始执行，正在等待阶段更新。',
        lastError: null,
      },
    };
  }

  if (event.event_type === 'task.progress') {
    const payload = event.payload;
    const fallback = getNodePresentation(workflow, (payload.node_key as string | null) ?? null);
    return {
      workflow,
      patch: {
        status: 'running',
        nodeKey: (payload.node_key as string | null) ?? null,
        nodeLabel: (payload.label as string | undefined) || fallback.label,
        description: fallback.description,
        percent: Number(payload.percent ?? 0),
        completedCount: Number(payload.completed_count ?? 0),
        totalCount: Number(payload.total_count ?? (workflow === 'animation' ? 3 : 2)),
        detail: payload,
        lastError: null,
      },
    };
  }

  if (event.event_type === 'task.completed') {
    return {
      workflow,
      patch: {
        status: 'success',
        percent: 100,
        description: '任务执行完成。',
        lastError: null,
      },
    };
  }

  if (event.event_type === 'task.failed') {
    return {
      workflow,
      patch: {
        status: 'error',
        description: '任务执行失败。',
        lastError: (event.payload.message as string | undefined) || '任务执行失败',
      },
    };
  }

  if (event.event_type === 'task.cancelled') {
    return {
      workflow,
      patch: {
        status: 'error',
        description: '任务已取消。',
        lastError: '任务已取消',
      },
    };
  }

  return null;
};

export const toLogEntry = (event: TaskEventRecord): { content: string; details?: string } | null => {
  if (event.event_type === 'task.progress') {
    const label = event.payload.label as string | undefined;
    return { content: label ? `进度更新：${label}` : '进度更新。' };
  }

  if (event.event_type === 'workflow.node_completed') {
    return {
      content: `节点完成：${event.node_key || 'unknown'}`,
      details: JSON.stringify(event.payload, null, 2),
    };
  }

  if (event.event_type === 'artifact.published') {
    return {
      content: `产物已发布：${String(event.payload.artifact_type || 'unknown')}`,
      details: JSON.stringify(event.payload, null, 2),
    };
  }

  if (event.event_type === 'validation.failed') {
    return {
      content: '校验失败，存在需要处理的镜头问题。',
      details: JSON.stringify(event.payload, null, 2),
    };
  }

  if (event.event_type.startsWith('task.')) {
    const suffix = event.event_type.replace('task.', '');
    return {
      content: `任务状态变更：${formatEventType(suffix)}`,
      details: Object.keys(event.payload).length ? JSON.stringify(event.payload, null, 2) : undefined,
    };
  }

  return {
    content: `事件：${formatEventType(event.event_type)}`,
    details: Object.keys(event.payload).length ? JSON.stringify(event.payload, null, 2) : undefined,
  };
};
