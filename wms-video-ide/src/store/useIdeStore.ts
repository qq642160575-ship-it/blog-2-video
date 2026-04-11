import { create } from 'zustand';
import type { Scene } from '../types/scene';
import type { WorkflowHistoryItem, WorkflowName } from '../types/workflow';

export type AiStatus = 'idle' | 'generating' | 'error';
export type RewriteStatus = 'idle' | 'generating' | 'error' | 'success';

export interface IdeState {
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
  historyItems: WorkflowHistoryItem[];
  historyLoading: boolean;
  setSourceText: (text: string) => void;
  setOralScript: (text: string) => void;
  setScenes: (scenes: Scene[]) => void;
  setActiveScene: (id: string) => void;
  setAiStatus: (status: AiStatus) => void;
  setRewriteStatus: (status: RewriteStatus) => void;
  setScriptThreadContext: (threadId: string | null, checkpointId?: string | null) => void;
  setAnimationThreadContext: (threadId: string | null, checkpointId?: string | null) => void;
  setHistoryWorkflow: (workflow: WorkflowName | null) => void;
  setHistoryItems: (items: WorkflowHistoryItem[]) => void;
  setHistoryLoading: (loading: boolean) => void;
  updateSceneCode: (id: string, newCode: string) => void;
  updateSceneDuration: (id: string, durationInFrames: number) => void;
  updateSceneMark: (sceneId: string, markKey: string, newFrame: number) => void;
  updateSceneScript: (id: string, newScript: string) => void;
  addProcessLog: (content: string, details?: string) => void;
  clearProcessLogs: () => void;
  setProcessStartTime: (time: number | null) => void;
}

const DEFAULT_SOURCE_TEXT =
  '在 WMS 系统中，入库单的状态流转非常关键。从最初的 CREATED 到 ARRIVED，每一步都需要校验库存掩码，防止并发导致的数据冲突。';

export const useIdeStore = create<IdeState>((set) => ({
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
  historyItems: [],
  historyLoading: false,

  setSourceText: (text) => set({ sourceText: text }),
  setOralScript: (text) => set({ oralScript: text }),
  setScenes: (scenes) => set({ scenes, activeSceneId: scenes[0]?.id ?? '' }),
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
  setHistoryItems: (items) => set({ historyItems: items }),
  setHistoryLoading: (loading) => set({ historyLoading: loading }),

  addProcessLog: (content, details) =>
    set((state) => {
      const time = new Date().toLocaleTimeString('zh-CN', { hour12: false });
      return { processLogs: [...state.processLogs, { time, content, details }] };
    }),
  clearProcessLogs: () => set({ processLogs: [], processStartTime: null }),
  setProcessStartTime: (time) => set({ processStartTime: time }),

  updateSceneCode: (id, newCode) =>
    set((state) => ({
      scenes: state.scenes.map((s) => (s.id === id ? { ...s, code: newCode } : s)),
    })),

  updateSceneDuration: (id, durationInFrames) =>
    set((state) => ({
      scenes: state.scenes.map((s) => (s.id === id ? { ...s, durationInFrames } : s)),
    })),

  updateSceneMark: (sceneId, markKey, newFrame) =>
    set((state) => ({
      scenes: state.scenes.map((s) =>
        s.id === sceneId ? { ...s, marks: { ...s.marks, [markKey]: newFrame } } : s
      ),
    })),

  updateSceneScript: (id, newScript) =>
    set((state) => ({
      scenes: state.scenes.map((s) => (s.id === id ? { ...s, script: newScript } : s)),
    })),
}));
