import type { WorkflowName } from '../types/workflow';

export type CompatSsePayload = {
  type: string;
  message?: string;
  data?: Record<string, unknown>;
  thread_id?: string;
  checkpoint_id?: string | null;
  workflow?: WorkflowName;
  progress?: {
    status?: 'idle' | 'running' | 'success' | 'error';
    node_key?: string | null;
    node_label?: string;
    description?: string;
    completed_count?: number;
    total_count?: number;
    percent?: number;
    elapsed_seconds?: number;
    eta_seconds?: number | null;
    estimated_total_seconds?: number | null;
    detail?: Record<string, unknown>;
  };
};
