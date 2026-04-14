import type { WorkflowName } from '../types/workflow';

export type WorkflowProgressStatus = 'idle' | 'running' | 'success' | 'error';

export interface WorkflowProgress {
  workflow: WorkflowName;
  nodeKey: string | null;
  nodeLabel: string;
  description: string;
  status: WorkflowProgressStatus;
  completedCount: number;
  totalCount: number;
  percent: number;
  elapsedSeconds: number;
  etaSeconds: number | null;
  estimatedTotalSeconds: number | null;
  detail: Record<string, unknown>;
  updatedAt: number | null;
  lastError: string | null;
}

const WORKFLOW_LABELS: Record<WorkflowName, string> = {
  conversational_tone: '口播脚本',
  animation: '分镜生成',
};

const NODE_LABELS: Record<string, { label: string; description: string; stage: 'langgraph' | 'enhancement' }> = {
  content_writer: {
    label: '正在改写口播稿',
    description: '系统会把原文改写成更适合视频口播的表达。',
    stage: 'langgraph',
  },
  content_reviewer: {
    label: '正在评估口播效果',
    description: '系统会检查节奏、清晰度和可讲述性，再决定是否继续优化。',
    stage: 'langgraph',
  },
  director_node: {
    label: '正在拆分镜头',
    description: '系统会把口播稿拆成镜头段落，并为每段安排基本时长。',
    stage: 'langgraph',
  },
  visual_architect_node: {
    label: '正在设计视觉方案',
    description: '系统会为镜头补充视觉风格、画面结构和动画提示。',
    stage: 'langgraph',
  },
  style_analysis: {
    label: '正在分析视觉风格',
    description: '系统正在使用 AI 分析内容，推荐最合适的视觉风格和配色方案。',
    stage: 'enhancement',
  },
  layout_generation: {
    label: '正在生成场景布局',
    description: '系统正在为每个场景设计布局和视觉元素排列。',
    stage: 'enhancement',
  },
  render_preview: {
    label: '正在渲染场景预览',
    description: '系统正在为每个场景生成预览图像。',
    stage: 'enhancement',
  },
  coder_node: {
    label: '正在生成镜头代码',
    description: '系统会把镜头设计翻译成可预览、可继续编辑的代码。',
    stage: 'langgraph',
  },
};

export const getWorkflowLabel = (workflow: WorkflowName) => WORKFLOW_LABELS[workflow];

export const createDefaultWorkflowProgress = (
  workflow: WorkflowName
): WorkflowProgress => ({
  workflow,
  nodeKey: null,
  nodeLabel: `${getWorkflowLabel(workflow)}未开始`,
  description: '流程还没有开始，生成后这里会显示当前进度。',
  status: 'idle',
  completedCount: 0,
  totalCount: workflow === 'animation' ? 3 : 2,
  percent: 0,
  elapsedSeconds: 0,
  etaSeconds: null,
  estimatedTotalSeconds: null,
  detail: {},
  updatedAt: null,
  lastError: null,
});

export const getNodePresentation = (workflow: WorkflowName, nodeKey: string | null) => {
  if (nodeKey && NODE_LABELS[nodeKey]) {
    return NODE_LABELS[nodeKey];
  }

  return {
    label: `${getWorkflowLabel(workflow)}处理中`,
    description: '系统正在处理当前阶段，请稍候。',
  };
};

export const formatWorkflowAction = (workflow: WorkflowName, action?: string | null) => {
  if (!action) {
    return `${getWorkflowLabel(workflow)}阶段`;
  }

  return action
    .replace('content_writer', '改写口播稿')
    .replace('content_reviewer', '评估口播效果')
    .replace('director_node', '拆分镜头')
    .replace('visual_architect_node', '设计视觉方案')
    .replace('style_analysis', '分析视觉风格')
    .replace('layout_generation', '生成场景布局')
    .replace('coder_node', '生成镜头代码');
};
