from __future__ import annotations


class AppError(Exception):
    def __init__(self, code: str, message: str, detail: dict | None = None) -> None:
        self.code = code
        self.message = message
        self.detail = detail or {}
        super().__init__(message)


class SessionNotFoundError(AppError):
    def __init__(self, session_id: str) -> None:
        super().__init__(
            code="SESSION_NOT_FOUND",
            message=f"Session not found: {session_id}",
            detail={"session_id": session_id},
        )


class BranchNotFoundError(AppError):
    def __init__(self, branch_id: str) -> None:
        super().__init__(
            code="BRANCH_NOT_FOUND",
            message=f"Branch not found: {branch_id}",
            detail={"branch_id": branch_id},
        )


class TaskNotFoundError(AppError):
    def __init__(self, task_id: str) -> None:
        super().__init__(
            code="TASK_NOT_FOUND",
            message=f"Task not found: {task_id}",
            detail={"task_id": task_id},
        )


class InvalidTaskStateError(AppError):
    def __init__(self, task_id: str, current_state: str, expected_state: str) -> None:
        super().__init__(
            code="INVALID_TASK_STATE",
            message=f"Task {task_id} is in state {current_state}, expected {expected_state}",
            detail={
                "task_id": task_id,
                "current_state": current_state,
                "expected_state": expected_state,
            },
        )


class ArtifactNotFoundError(AppError):
    def __init__(self, artifact_id: str) -> None:
        super().__init__(
            code="ARTIFACT_NOT_FOUND",
            message=f"Artifact not found: {artifact_id}",
            detail={"artifact_id": artifact_id},
        )


class BaselineConflictError(AppError):
    def __init__(self, branch_id: str, expected_version: int, actual_version: int) -> None:
        super().__init__(
            code="BASELINE_CONFLICT",
            message="当前分支已经有新版本，请刷新后重试。",
            detail={
                "branch_id": branch_id,
                "expected_version": expected_version,
                "actual_version": actual_version,
            },
        )


class SceneLockedError(AppError):
    def __init__(self, scene_id: str, branch_id: str) -> None:
        super().__init__(
            code="SCENE_LOCKED",
            message=f"Scene {scene_id} is locked by another task",
            detail={"scene_id": scene_id, "branch_id": branch_id},
        )


class WorkflowFailedError(AppError):
    def __init__(self, workflow_name: str, reason: str) -> None:
        super().__init__(
            code="WORKFLOW_FAILED",
            message=f"Workflow {workflow_name} failed: {reason}",
            detail={"workflow_name": workflow_name, "reason": reason},
        )


class LLMOutputInvalidError(AppError):
    def __init__(self, agent_name: str, reason: str) -> None:
        super().__init__(
            code="LLM_OUTPUT_INVALID",
            message=f"LLM output from {agent_name} is invalid: {reason}",
            detail={"agent_name": agent_name, "reason": reason},
        )


class ValidationFailedError(AppError):
    def __init__(self, scene_id: str, error_count: int) -> None:
        super().__init__(
            code="VALIDATION_FAILED",
            message=f"Scene {scene_id} validation failed with {error_count} errors",
            detail={"scene_id": scene_id, "error_count": error_count},
        )


class RepairFailedError(AppError):
    def __init__(self, scene_id: str, reason: str) -> None:
        super().__init__(
            code="REPAIR_FAILED",
            message=f"Scene {scene_id} repair failed: {reason}",
            detail={"scene_id": scene_id, "reason": reason},
        )


class RenderFailedError(AppError):
    def __init__(self, scene_id: str, reason: str) -> None:
        super().__init__(
            code="RENDER_FAILED",
            message=f"Scene {scene_id} render failed: {reason}",
            detail={"scene_id": scene_id, "reason": reason},
        )
