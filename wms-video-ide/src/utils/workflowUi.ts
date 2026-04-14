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

const NODE_LABELS: Record<string, { label: string; description: string }> = {
  rewrite_oral_script_node: {
    label: '正在改写口播稿',
    description: '系统会把原文改写成更适合视频口播的表达。',
  },
  review_oral_script_node: {
    label: '正在评估口播效果',
    description: '系统会检查节奏、清晰度和可讲述性，再决定是否继续优化。',
  },
  finalize_oral_script_node: {
    label: '正在整理口播段落',
    description: '系统会切分讲述段落，并生成口语稿结构化结果。',
  },
  parse_oral_script_node: {
    label: '正在解析口语稿',
    description: '把口语稿整理成可编译的讲述结构',
  },
  plan_scenes_node: {
    label: '正在规划分镜顺序',
    description: '确定顺序并分配场景模板位',
  },
  generate_marks_node: {
    label: '正在构建时间轴引擎',
    description: '拍表估算锁定全量持续时间',
  },
  compile_layout_node: {
    label: '正在编译安全区布局',
    description: '处理盒子归一化与边界防溢出',
  },
  compile_motion_node: {
    label: '正在绑定动画流',
    description: '进行严格的出入场时序映射',
  },
  generate_dsl_node: {
    label: '正在生成中间语法树',
    description: '将空间与动画数据凝聚为AST',
  },
  generate_scene_code_node: {
    label: '正在模板化注入代码',
    description: '排除模型幻觉确保绝对代码安全',
  },
  validate_scene_node: {
    label: '正在发起静态巡检',
    description: '检查悬空指针、错误坐标与非法引用',
  },
  repair_scene_node: {
    label: '正在处理自愈与对齐',
    description: '对不合法场景触发降级逻辑',
  },
  finalize_output_node: {
    label: '正在执行封装验收',
    description: '确认所有的生成和修复环节完毕',
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
  totalCount: workflow === 'animation' ? 10 : 3,
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
    .replace('rewrite_oral_script_node', '改写口播稿')
    .replace('review_oral_script_node', '评估口播效果')
    .replace('finalize_oral_script_node', '整理口播段落')
    .replace('parse_oral_script_node', '解析口语稿')
    .replace('plan_scenes_node', '规划分镜')
    .replace('generate_marks_node', '时间轴构建')
    .replace('compile_layout_node', '布局编译')
    .replace('compile_motion_node', '动画编译')
    .replace('generate_dsl_node', 'AST树生成')
    .replace('generate_scene_code_node', '代码模板化')
    .replace('validate_scene_node', '校验')
    .replace('repair_scene_node', '自愈')
    .replace('finalize_output_node', '封装验收');
};
