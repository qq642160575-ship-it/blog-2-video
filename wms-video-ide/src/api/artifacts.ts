import { fetchJson, postJson } from './client';
import type { ArtifactResponse, BranchResponse, SceneArtifactResponse } from '../types/artifact';

export const getArtifact = (artifactId: string) =>
  fetchJson<ArtifactResponse>(`/api/artifacts/${encodeURIComponent(artifactId)}`);

export const getSceneArtifact = (sceneArtifactId: string) =>
  fetchJson<SceneArtifactResponse>(
    `/api/scene-artifacts/${encodeURIComponent(sceneArtifactId)}`
  );

export const listBranchArtifacts = (branchId: string) =>
  fetchJson<{ items: ArtifactResponse[] }>(`/api/branches/${encodeURIComponent(branchId)}/artifacts`);

export const branchFromArtifact = (artifactId: string) =>
  postJson<BranchResponse>(`/api/artifacts/${encodeURIComponent(artifactId)}/branch`, {});
