from __future__ import annotations

from typing import Any

from domain.artifacts.entities import ArtifactRecord, SceneArtifactRecord
from domain.common.enums import ArtifactType
from orchestration.event_publisher import InMemoryEventPublisher
from persistence.repositories import InMemoryArtifactRepository, InMemoryBranchRepository


class ArtifactService:
    def __init__(
        self,
        artifact_repo: InMemoryArtifactRepository,
        branch_repo: InMemoryBranchRepository,
        event_publisher: InMemoryEventPublisher,
    ) -> None:
        self.artifact_repo = artifact_repo
        self.branch_repo = branch_repo
        self.event_publisher = event_publisher

    async def publish_artifact(
        self,
        *,
        session_id: str,
        branch_id: str,
        task_id: str | None,
        artifact_type: ArtifactType,
        artifact_subtype: str | None = None,
        content_json: dict[str, Any] | None = None,
        content_text: str | None = None,
        storage_url: str | None = None,
        summary: str | None = None,
        parent_artifact_id: str | None = None,
        publish_event: bool = True,
    ) -> ArtifactRecord:
        version = await self.artifact_repo.next_version(
            branch_id,
            artifact_type.value,
            artifact_subtype,
        )
        artifact = ArtifactRecord(
            session_id=session_id,
            branch_id=branch_id,
            task_id=task_id,
            artifact_type=artifact_type,
            artifact_subtype=artifact_subtype,
            version=version,
            content_json=content_json,
            content_text=content_text,
            storage_url=storage_url,
            summary=summary,
            parent_artifact_id=parent_artifact_id,
        )
        await self.artifact_repo.publish(artifact)
        branch = await self.branch_repo.get(branch_id)
        if branch is not None:
            await self.branch_repo.update_head(branch_id, branch.version, artifact.id)
        if publish_event and task_id is not None:
            await self.event_publisher.publish(
                "artifact.published",
                task_id=task_id,
                session_id=session_id,
                branch_id=branch_id,
                payload={
                    "artifact_id": artifact.id,
                    "artifact_type": artifact.artifact_type.value,
                    "artifact_subtype": artifact.artifact_subtype,
                    "version": artifact.version,
                    "summary": summary,
                    "data": artifact.content_json,
                },
            )
        return artifact

    async def publish_scene_artifact(
        self,
        *,
        bundle_artifact: ArtifactRecord,
        scene_id: str,
        scene_order: int,
        scene_type: str | None = None,
        script_text: str | None = None,
        visual_intent: dict[str, Any] | None = None,
        layout_spec: dict[str, Any] | None = None,
        code_text: str | None = None,
        validation_report: dict[str, Any] | None = None,
        preview_image_url: str | None = None,
        status: str = "ready",
    ) -> SceneArtifactRecord:
        version = await self.artifact_repo.next_scene_version(
            bundle_artifact.session_id,
            bundle_artifact.branch_id,
            scene_id,
        )
        scene_artifact = SceneArtifactRecord(
            artifact_id=bundle_artifact.id,
            session_id=bundle_artifact.session_id,
            branch_id=bundle_artifact.branch_id,
            scene_id=scene_id,
            scene_order=scene_order,
            scene_type=scene_type,
            script_text=script_text,
            visual_intent=visual_intent,
            layout_spec=layout_spec,
            code_text=code_text,
            validation_report=validation_report,
            preview_image_url=preview_image_url,
            status=status,
            version=version,
        )
        await self.artifact_repo.publish_scene_artifact(scene_artifact)
        return scene_artifact
