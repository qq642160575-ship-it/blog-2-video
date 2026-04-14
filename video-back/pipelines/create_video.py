from __future__ import annotations

from domain.common.enums import ArtifactType
from orchestration.task_context import PipelineResult, TaskContext
from orchestration.workflow_runner import WorkflowRunner
from persistence.repositories import InMemoryArtifactRepository


class CreateVideoPipeline:
    name = "create_video"

    def __init__(
        self,
        workflow_runner: WorkflowRunner,
        artifact_repo: InMemoryArtifactRepository,
    ) -> None:
        self.workflow_runner = workflow_runner
        self.artifact_repo = artifact_repo

    async def run(self, context: TaskContext) -> PipelineResult:
        source_artifact_id = context.request_payload["source_artifact_id"]
        source_artifact = await self.artifact_repo.get(source_artifact_id)
        if source_artifact is None:
            raise ValueError(f"Source artifact not found: {source_artifact_id}")
        if source_artifact.artifact_type != ArtifactType.SOURCE_DOCUMENT:
            raise ValueError("create_video requires a source_document artifact")

        result = await self.workflow_runner.run_animation(
            context=context,
            script=source_artifact.content_text or "",
        )
        return PipelineResult(
            summary={
                "artifact_count": len(result["artifact_ids"]),
                "scene_count": len(result["scene_artifact_ids"]),
                "failed_scenes": result["failed_scenes"],
            },
            artifact_ids=result["artifact_ids"],
            scene_artifact_ids=result["scene_artifact_ids"],
        )
