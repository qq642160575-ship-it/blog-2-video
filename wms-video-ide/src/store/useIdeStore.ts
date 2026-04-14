import { create } from 'zustand';
import type { Scene } from '../types/scene';
import type { WorkflowHistoryItem, WorkflowName } from '../types/workflow';
import {
  createDefaultWorkflowProgress,
  type WorkflowProgress,
  type WorkflowProgressStatus,
} from '../utils/workflowUi';

export type AiStatus = 'idle' | 'generating' | 'error';
export type RewriteStatus = 'idle' | 'generating' | 'error' | 'success';

import type { PipelineStage, PipelineError, ParsedScript } from '../types/pipeline';
import type { SceneSpec, MarksSpec, LayoutSpec, MotionSpec, DslSpec, SceneCodeSpec, ValidationSpec } from '../types/artifacts';

export interface ArtifactState {
  parsedScript: ParsedScript | null;
  scenePlan: SceneSpec[];
  marks: MarksSpec | null;
  layouts: Record<string, LayoutSpec>;
  motions: Record<string, MotionSpec>;
  dsl: Record<string, DslSpec>;
  codes: Record<string, SceneCodeSpec>;
  validations: Record<string, ValidationSpec>;
}

export type ArtifactTab = 'script' | 'scenes' | 'marks' | 'layout' | 'motion' | 'dsl' | 'code' | 'validation' | 'logs';

export interface UiState {
  activeTab: ArtifactTab;
  selectedRecompileFrom: 'layout' | 'motion' | 'dsl' | 'code';
  isDevMode: boolean;
  expandedPanels: string[];
}

export interface PipelineState {
  pipelineStage: PipelineStage;
  lastError: PipelineError | null;
}

export interface IdeState extends PipelineState, ArtifactState, UiState {
  sourceText: string;
  oralScript: string;
  scenes: Scene[];
  activeSceneId: string;
  aiStatus: AiStatus;
  rewriteStatus: RewriteStatus;
  processLogs: { time: string; content: string; details?: string }[];
  processStartTime: number | null;
  scriptThreadId: string | null;
  scriptCheckpointId: string | null;
  animationThreadId: string | null;
  animationCheckpointId: string | null;
  historyWorkflow: WorkflowName | null;
  historyItemsByWorkflow: Record<WorkflowName, WorkflowHistoryItem[]>;
  historyLoadingByWorkflow: Record<WorkflowName, boolean>;
  workflowProgressByName: Record<WorkflowName, WorkflowProgress>;
  scriptBaseline: { sourceText: string; oralScript: string } | null;
  animationBaseline: string;
  setSourceText: (text: string) => void;
  setOralScript: (text: string) => void;
  setScenes: (scenes: Scene[]) => void;
  setActiveScene: (id: string) => void;
  setAiStatus: (status: AiStatus) => void;
  setRewriteStatus: (status: RewriteStatus) => void;
  setScriptThreadContext: (threadId: string | null, checkpointId?: string | null) => void;
  setAnimationThreadContext: (threadId: string | null, checkpointId?: string | null) => void;
  setHistoryWorkflow: (workflow: WorkflowName | null) => void;
  setHistoryItems: (workflow: WorkflowName, items: WorkflowHistoryItem[]) => void;
  setHistoryLoading: (workflow: WorkflowName, loading: boolean) => void;
  setWorkflowProgress: (
    workflow: WorkflowName,
    patch: Partial<WorkflowProgress> & { status?: WorkflowProgressStatus }
  ) => void;
  resetWorkflowProgress: (workflow: WorkflowName) => void;
  captureScriptBaseline: () => void;
  captureAnimationBaseline: () => void;
  updateSceneCode: (id: string, newCode: string) => void;
  updateSceneDuration: (id: string, durationInFrames: number) => void;
  updateSceneMark: (sceneId: string, markKey: string, newFrame: number) => void;
  updateSceneScript: (id: string, newScript: string, newDesign: string) => void;
  addProcessLog: (content: string, details?: string) => void;
  clearProcessLogs: () => void;
  setProcessStartTime: (time: number | null) => void;
  loadHistory: (workflow: WorkflowName) => Promise<void>;
  setPipelineStage: (stage: PipelineStage) => void;
  setPipelineError: (error: PipelineError | null) => void;
  setActiveTab: (tab: ArtifactTab) => void;
  updateArtifacts: (patch: Partial<ArtifactState>) => void;
}

const DEFAULT_SOURCE_TEXT =
  '在 WMS 系统中，入库单的状态流转非常关键。从最初的 CREATED 到 ARRIVED，每一步都需要校验库存掩码，防止并发导致的数据冲突。';

const normalizeDuration = (durationInFrames: number): number =>
  Math.max(1, Math.round(Number.isFinite(durationInFrames) ? durationInFrames : 150));

const normalizeMarks = (
  marks: Record<string, number> | undefined,
  durationInFrames: number
): Record<string, number> => {
  const maxFrame = Math.max(0, normalizeDuration(durationInFrames) - 1);

  return Object.fromEntries(
    Object.entries(marks ?? {})
      .filter(([, frame]) => Number.isFinite(frame))
      .map(
        ([key, frame]): [string, number] => [
          key,
          Math.min(maxFrame, Math.max(0, Math.round(frame))),
        ]
      )
      .sort((a, b) => a[1] - b[1] || a[0].localeCompare(b[0]))
  );
};

const normalizeScene = (scene: Scene): Scene => {
  const durationInFrames = normalizeDuration(scene.durationInFrames);
  return {
    ...scene,
    durationInFrames,
    marks: normalizeMarks(scene.marks, durationInFrames),
  };
};

export const useIdeStore = create<IdeState>((set, get) => ({
  // PipelineState
  pipelineStage: 'idle',
  lastError: null,

  // ArtifactState
  parsedScript: null,
  scenePlan: [],
  marks: null,
  layouts: {},
  motions: {},
  dsl: {},
  codes: {},
  validations: {},

  // UiState
  activeTab: 'progress' as const as ArtifactTab, // Fallback for backward compatibility
  selectedRecompileFrom: 'layout',
  isDevMode: true,
  expandedPanels: [],

  // legacy
  sourceText: DEFAULT_SOURCE_TEXT,
  oralScript: '',
  scenes: [],
  activeSceneId: '',
  aiStatus: 'idle',
  rewriteStatus: 'idle',
  processLogs: [],
  processStartTime: null,
  scriptThreadId: null,
  scriptCheckpointId: null,
  animationThreadId: null,
  animationCheckpointId: null,
  historyWorkflow: null,
  historyItemsByWorkflow: {
    conversational_tone: [],
    animation: [],
  },
  historyLoadingByWorkflow: {
    conversational_tone: false,
    animation: false,
  },
  workflowProgressByName: {
    conversational_tone: createDefaultWorkflowProgress('conversational_tone'),
    animation: createDefaultWorkflowProgress('animation'),
  },
  scriptBaseline: null,
  animationBaseline: '[]',

  setSourceText: (text) => set({ sourceText: text }),
  setOralScript: (text) => set({ oralScript: text }),
  setPipelineStage: (stage) => set({ pipelineStage: stage }),
  setPipelineError: (error) => set({ lastError: error }),
  setActiveTab: (tab) => set({ activeTab: tab }),
  updateArtifacts: (patch) => set((state) => ({ ...state, ...patch })),
  setScenes: (scenes) => {
    const normalizedScenes = scenes.map(normalizeScene);
    set({ scenes: normalizedScenes, activeSceneId: normalizedScenes[0]?.id ?? '' });
  },
  setActiveScene: (id) => set({ activeSceneId: id }),
  setAiStatus: (status) => set({ aiStatus: status }),
  setRewriteStatus: (status) => set({ rewriteStatus: status }),
  setScriptThreadContext: (threadId, checkpointId = null) =>
    set((state) => ({
      scriptThreadId: threadId,
      scriptCheckpointId: checkpointId ?? state.scriptCheckpointId,
    })),
  setAnimationThreadContext: (threadId, checkpointId = null) =>
    set((state) => ({
      animationThreadId: threadId,
      animationCheckpointId: checkpointId ?? state.animationCheckpointId,
    })),
  setHistoryWorkflow: (workflow) => set({ historyWorkflow: workflow }),
  setHistoryItems: (workflow, items) =>
    set((state) => ({
      historyItemsByWorkflow: { ...state.historyItemsByWorkflow, [workflow]: items },
    })),
  setHistoryLoading: (workflow, loading) =>
    set((state) => ({
      historyLoadingByWorkflow: { ...state.historyLoadingByWorkflow, [workflow]: loading },
    })),
  setWorkflowProgress: (workflow, patch) =>
    set((state) => ({
      workflowProgressByName: {
        ...state.workflowProgressByName,
        [workflow]: {
          ...state.workflowProgressByName[workflow],
          ...patch,
          workflow,
          updatedAt: patch.updatedAt ?? Date.now(),
        },
      },
    })),
  resetWorkflowProgress: (workflow) =>
    set((state) => ({
      workflowProgressByName: {
        ...state.workflowProgressByName,
        [workflow]: createDefaultWorkflowProgress(workflow),
      },
    })),
  captureScriptBaseline: () =>
    set((state) => ({
      scriptBaseline: {
        sourceText: state.sourceText,
        oralScript: state.oralScript,
      },
    })),
  captureAnimationBaseline: () =>
    set((state) => ({
      animationBaseline: JSON.stringify(state.scenes),
    })),

  addProcessLog: (content, details) =>
    set((state) => {
      const time = new Date().toLocaleTimeString('zh-CN', { hour12: false });
      return { processLogs: [...state.processLogs, { time, content, details }] };
    }),
  clearProcessLogs: () => set({ processLogs: [], processStartTime: null }),
  setProcessStartTime: (time) => set({ processStartTime: time }),

  updateSceneCode: (id, newCode) =>
    set((state) => ({
      scenes: state.scenes.map((scene) =>
        scene.id === id ? { ...scene, code: newCode } : scene
      ),
    })),

  updateSceneDuration: (id, durationInFrames) =>
    set((state) => ({
      scenes: state.scenes.map((scene) =>
        scene.id === id
          ? normalizeScene({ ...scene, durationInFrames: normalizeDuration(durationInFrames) })
          : scene
      ),
    })),

  updateSceneMark: (sceneId, markKey, newFrame) =>
    set((state) => ({
      scenes: state.scenes.map((scene) =>
        scene.id === sceneId
          ? normalizeScene({ ...scene, marks: { ...scene.marks, [markKey]: newFrame } })
          : scene
      ),
    })),

  updateSceneScript: (id, newScript, newDesign) =>
    set((state) => ({
      scenes: state.scenes.map((scene) =>
        scene.id === id
          ? { ...scene, script: newScript, visual_design: newDesign }
          : scene
      ),
    })),

  loadHistory: async (workflow) => {
    const state = get();
    const threadId =
      workflow === 'conversational_tone'
        ? state.scriptThreadId
        : state.animationThreadId;
    if (!threadId) return;

    set((currentState) => ({
      historyWorkflow: workflow,
      historyLoadingByWorkflow: {
        ...currentState.historyLoadingByWorkflow,
        [workflow]: true,
      },
    }));
    try {
      const response = await fetch(
        `/api/workflows/${workflow}/history?thread_id=${encodeURIComponent(threadId)}&limit=12`
      );
      if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
      const data = await response.json();
      set((currentState) => ({
        historyItemsByWorkflow: {
          ...currentState.historyItemsByWorkflow,
          [workflow]: data.items ?? [],
        },
      }));
    } catch (error) {
      console.error('loadHistory error:', error);
    } finally {
      set((currentState) => ({
        historyLoadingByWorkflow: {
          ...currentState.historyLoadingByWorkflow,
          [workflow]: false,
        },
      }));
    }
  },
}));
