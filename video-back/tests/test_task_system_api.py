import asyncio

import pytest

import app.dependencies as deps
from api.routes import create_session, create_task, get_task, list_branch_artifacts, list_task_events
from api.schemas import CreateSessionRequest, CreateTaskRequest
from app.dependencies import AppContainer
from domain.common.enums import ArtifactType, TaskType
from orchestration.task_context import PipelineResult


class FakeCreateVideoPipeline:
    name = "create_video"

    def __init__(self, container: AppContainer) -> None:
        self.container = container

    async def run(self, context):
        source_artifact = await self.container.artifact_repo.get(
            context.request_payload["source_artifact_id"]
        )
        artifact = await self.container.artifact_service.publish_artifact(
            session_id=context.task.session_id,
            branch_id=context.task.branch_id,
            task_id=context.task.id,
            artifact_type=ArtifactType.SCRIPT,
            content_text=source_artifact.content_text if source_artifact else "",
            summary="fake script artifact",
        )
        return PipelineResult(
            summary={"ok": True},
            artifact_ids=[artifact.id],
            scene_artifact_ids=[],
        )


@pytest.fixture
async def isolated_container(monkeypatch):
    container = AppContainer(use_real_workflow=False)
    container.dispatcher._pipelines[TaskType.CREATE_VIDEO] = FakeCreateVideoPipeline(container)
    monkeypatch.setattr(deps, "_container", container)
    await container.start()
    try:
        yield container
    finally:
        await container.stop()


@pytest.mark.anyio
async def test_create_session_creates_source_artifact(isolated_container):
    response = await create_session(
        CreateSessionRequest(
            source_type="text",
            source_content="hello world",
            title="demo",
        )
    )
    branch_id = response.branch_id

    artifact_response = await list_branch_artifacts(branch_id)
    artifacts = artifact_response["items"]
    assert len(artifacts) == 1
    assert artifacts[0]["artifact_type"] == ArtifactType.SOURCE_DOCUMENT


@pytest.mark.anyio
async def test_create_task_runs_pipeline_and_emits_events(isolated_container):
    session_response = await create_session(
        CreateSessionRequest(
            source_type="text",
            source_content="task source",
            title="demo",
        )
    )
    branch_id = session_response.branch_id
    artifacts_response = await list_branch_artifacts(branch_id)
    source_artifact_id = artifacts_response["items"][0]["artifact_id"]

    task_response = await create_task(
        session_response.session_id,
        CreateTaskRequest(
            branch_id=branch_id,
            task_type=TaskType.CREATE_VIDEO,
            request_payload={"source_artifact_id": source_artifact_id},
            baseline_artifact_id=None,
        ),
    )
    task_id = task_response.task_id

    for _ in range(40):
        task_payload = await get_task(task_id)
        if task_payload["status"] == "succeeded":
            break
        await asyncio.sleep(0.05)

    assert task_payload["status"] == "succeeded"

    events_response = await list_task_events(task_id)
    event_types = [item["event_type"] for item in events_response["items"]]
    assert "task.created" in event_types
    assert "task.started" in event_types
    assert "artifact.published" in event_types
    assert "task.completed" in event_types
