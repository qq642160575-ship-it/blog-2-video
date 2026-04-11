export type WorkflowName = 'conversational_tone' | 'animation';

export interface WorkflowTaskSnapshot {
  id: string | null;
  name: string | null;
  path: string[];
  error: string | null;
  interrupts: unknown[];
  result: unknown;
}

export interface WorkflowHistoryItem {
  checkpoint_id: string;
  thread_id: string;
  checkpoint_ns: string;
  parent_checkpoint_id: string | null;
  created_at: string | null;
  next_nodes: string[];
  values: Record<string, unknown>;
  metadata: Record<string, unknown>;
  step: number | null;
  source: string | null;
  tasks: WorkflowTaskSnapshot[];
}
