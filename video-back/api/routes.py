import json
import uuid
from typing import Any, AsyncIterator

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from api.schemas import (
    ArtifactResponse,
    BranchResponse,
    CreateSessionRequest,
    CreateSessionResponse,
    CreateTaskRequest,
    CreateTaskResponse,
    ForkRequest,
    GenerateRequest,
    RegenerateSceneRequest,
    ReplayRequest,
    SceneArtifactResponse,
    SessionOverviewResponse,
)
from app.dependencies import get_container
from domain.common.enums import ArtifactType, SessionStatus, TaskStatus, TaskType
from domain.sessions.entities import BranchRecord, SessionRecord
from domain.tasks.entities import TaskRecord
from utils.logger import get_logger

router = APIRouter()
logger = get_logger(__name__)


def _sse(payload: dict[str, Any]) -> str:
    return f"data: {json.dumps(payload, ensure_ascii=False, default=str)}\n\n"


async def _stream_task_events(task_id: str) -> AsyncIterator[str]:
    container = get_container()
    task = await container.task_repo.get(task_id)
    if task is None:
        yield _sse({"type": "error", "message": f"Task not found: {task_id}"})
        return

    terminal_statuses = {
        TaskStatus.SUCCEEDED,
        TaskStatus.FAILED,
        TaskStatus.CANCELLED,
    }

    # 先订阅，避免竞态条件
    queue = await container.event_repo.subscribe_task(task_id)
    try:
        # 发送历史事件
        existing = await container.event_repo.list_by_task(task_id)
        for event in existing:
            yield _sse(event.model_dump(mode="json"))

        # 检查任务是否已完成
        latest_task = await container.task_repo.get(task_id)
        if latest_task is not None and latest_task.status in terminal_statuses:
            return

        # 订阅实时事件
        while True:
            event = await queue.get()
            yield _sse(event.model_dump(mode="json"))
            latest_task = await container.task_repo.get(task_id)
            if latest_task is not None and latest_task.status in terminal_statuses:
                return
    finally:
        await container.event_repo.unsubscribe_task(task_id, queue)


def _to_legacy_payload(event: dict[str, Any], task_id: str) -> dict[str, Any]:
    event_type = event["event_type"]
    payload = event.get("payload") or {}
    if event_type == "task.progress":
        return {
            "type": "progress",
            "workflow": "animation",
            "thread_id": task_id,
            "progress": {
                "status": "running",
                "node_key": payload.get("node_key"),
                "node_label": payload.get("label"),
                "description": payload.get("label"),
                "percent": payload.get("percent"),
                "completed_count": payload.get("completed_count"),
                "total_count": payload.get("total_count"),
                "detail": payload,
            },
        }
    if event_type == "workflow.node_completed":
        return {
            "type": "updates",
            "workflow": "animation",
            "thread_id": task_id,
            "data": {event.get("node_key") or "node": payload.get("data", payload)},
        }
    if event_type == "task.failed":
        return {
            "type": "error",
            "workflow": "animation",
            "thread_id": task_id,
            "message": payload.get("message", "Task failed"),
        }
    if event_type == "task.completed":
        return {
            "type": "end",
            "workflow": "animation",
            "thread_id": task_id,
            "data": payload,
        }
    if event_type == "task.started":
        return {
            "type": "setup",
            "workflow": "animation",
            "thread_id": task_id,
            "progress": {
                "status": "running",
                "node_key": "director_node",
                "node_label": "正在拆分镜头",
                "description": "任务已开始执行。",
                "percent": 1,
                "completed_count": 0,
                "total_count": 3,
            },
        }
    return {
        "type": "updates",
        "workflow": "animation",
        "thread_id": task_id,
        "data": {"event_type": event_type, "payload": payload},
    }


async def _stream_legacy_task_events(task_id: str) -> AsyncIterator[str]:
    async for event_text in _stream_task_events(task_id):
        raw = event_text.removeprefix("data: ").strip()
        if not raw:
            continue
        event = json.loads(raw)
        yield _sse(_to_legacy_payload(event, task_id))


def _artifact_response(artifact) -> ArtifactResponse:
    return ArtifactResponse(
        artifact_id=artifact.id,
        session_id=artifact.session_id,
        branch_id=artifact.branch_id,
        task_id=artifact.task_id,
        artifact_type=artifact.artifact_type,
        artifact_subtype=artifact.artifact_subtype,
        version=artifact.version,
        content_json=artifact.content_json,
        content_text=artifact.content_text,
        storage_url=artifact.storage_url,
        summary=artifact.summary,
        parent_artifact_id=artifact.parent_artifact_id,
    )


def _scene_artifact_response(scene_artifact) -> SceneArtifactResponse:
    return SceneArtifactResponse(
        scene_artifact_id=scene_artifact.id,
        artifact_id=scene_artifact.artifact_id,
        session_id=scene_artifact.session_id,
        branch_id=scene_artifact.branch_id,
        scene_id=scene_artifact.scene_id,
        scene_order=scene_artifact.scene_order,
        scene_type=scene_artifact.scene_type,
        script_text=scene_artifact.script_text,
        visual_intent=scene_artifact.visual_intent,
        layout_spec=scene_artifact.layout_spec,
        code_text=scene_artifact.code_text,
        validation_report=scene_artifact.validation_report,
        preview_image_url=scene_artifact.preview_image_url,
        status=scene_artifact.status,
        version=scene_artifact.version,
    )


@router.post("/api/sessions", response_model=CreateSessionResponse)
async def create_session(req: CreateSessionRequest):
    container = get_container()
    session = SessionRecord(
        title=req.title,
        source_type=req.source_type,
        source_content=req.source_content,
        user_preference=(req.user_preference.model_dump() if req.user_preference else {}),
    )
    await container.session_repo.create(session)
    branch = BranchRecord(session_id=session.id)
    await container.branch_repo.create(branch)
    await container.session_repo.set_current_branch(session.id, branch.id)
    await container.artifact_service.publish_artifact(
        session_id=session.id,
        branch_id=branch.id,
        task_id=None,
        artifact_type=ArtifactType.SOURCE_DOCUMENT,
        content_text=req.source_content,
        content_json={
            "source_type": req.source_type,
            "title": req.title,
            "user_preference": req.user_preference.model_dump() if req.user_preference else {},
        },
        summary="源文档",
        publish_event=False,
    )
    return CreateSessionResponse(
        session_id=session.id,
        branch_id=branch.id,
        status=SessionStatus.ACTIVE,
    )


@router.get("/api/sessions/{session_id}", response_model=SessionOverviewResponse)
async def get_session(session_id: str):
    container = get_container()
    session = await container.session_repo.get(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return SessionOverviewResponse(
        session_id=session.id,
        title=session.title,
        source_type=session.source_type,
        status=session.status,
        current_branch_id=session.current_branch_id,
    )


@router.get("/api/sessions/{session_id}/timeline")
async def get_session_timeline(session_id: str, branch_id: str | None = None, limit: int = 100):
    container = get_container()
    session = await container.session_repo.get(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    events = await container.event_repo.list_timeline(session_id, branch_id=branch_id, limit=limit)
    return {"items": [event.model_dump(mode="json") for event in events]}


@router.post("/api/sessions/{session_id}/tasks", response_model=CreateTaskResponse)
async def create_task(session_id: str, req: CreateTaskRequest):
    container = get_container()
    session = await container.session_repo.get(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    branch = await container.branch_repo.get(req.branch_id)
    if branch is None or branch.session_id != session_id:
        raise HTTPException(status_code=404, detail="Branch not found")
    if req.baseline_artifact_id is not None:
        baseline_artifact = await container.artifact_repo.get(req.baseline_artifact_id)
        if baseline_artifact is None:
            raise HTTPException(status_code=404, detail="Baseline artifact not found")

    task = TaskRecord(
        session_id=session_id,
        branch_id=req.branch_id,
        task_type=req.task_type,
        request_payload=req.request_payload,
        baseline_artifact_id=req.baseline_artifact_id,
    )
    await container.task_repo.create(task)
    await container.event_publisher.publish(
        "task.created",
        task_id=task.id,
        session_id=task.session_id,
        branch_id=task.branch_id,
        payload={"task_type": task.task_type.value},
    )
    transitioned = await container.task_repo.transition(
        task.id,
        TaskStatus.PENDING.value,
        TaskStatus.QUEUED.value,
    )
    if not transitioned:
        raise HTTPException(status_code=409, detail="Failed to queue task")
    await container.event_publisher.publish(
        "task.queued",
        task_id=task.id,
        session_id=task.session_id,
        branch_id=task.branch_id,
        payload={"task_type": task.task_type.value},
    )
    await container.queue.enqueue(task.id, priority=task.priority)
    return CreateTaskResponse(task_id=task.id, status=TaskStatus.QUEUED)


@router.get("/api/tasks/{task_id}")
async def get_task(task_id: str):
    container = get_container()
    task = await container.task_repo.get(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return task.model_dump(mode="json")


@router.get("/api/tasks/{task_id}/events")
async def list_task_events(task_id: str):
    container = get_container()
    task = await container.task_repo.get(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    events = await container.event_repo.list_by_task(task_id)
    return {"items": [event.model_dump(mode="json") for event in events]}


@router.get("/api/tasks/{task_id}/events_sse")
async def task_events_sse(task_id: str):
    return StreamingResponse(_stream_task_events(task_id), media_type="text/event-stream")


@router.post("/api/tasks/{task_id}/cancel")
async def cancel_task(task_id: str):
    container = get_container()
    task = await container.task_repo.get(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")

    if task.status in {TaskStatus.SUCCEEDED, TaskStatus.FAILED, TaskStatus.CANCELLED}:
        return {"task_id": task.id, "status": task.status, "cancellation_requested": False}

    if task.status in {TaskStatus.PENDING, TaskStatus.QUEUED}:
        current_status = task.status.value
        transitioned = await container.task_repo.transition(
            task.id,
            current_status,
            TaskStatus.CANCELLED.value,
        )
        if transitioned:
            await container.event_publisher.publish(
                "task.cancelled",
                task_id=task.id,
                session_id=task.session_id,
                branch_id=task.branch_id,
            )
        updated = await container.task_repo.get(task_id)
        return {
            "task_id": task.id,
            "status": updated.status if updated else TaskStatus.CANCELLED,
            "cancellation_requested": False,
        }

    await container.task_repo.update(task.id, cancellation_requested=True)
    await container.event_publisher.publish(
        "task.cancel_requested",
        task_id=task.id,
        session_id=task.session_id,
        branch_id=task.branch_id,
    )
    updated = await container.task_repo.get(task_id)
    return {
        "task_id": task.id,
        "status": updated.status if updated else task.status,
        "cancellation_requested": True,
    }


@router.post("/api/tasks/{task_id}/retry")
async def retry_task(task_id: str):
    container = get_container()
    task = await container.task_repo.get(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    if task.status != TaskStatus.FAILED:
        raise HTTPException(status_code=409, detail="Only failed tasks can be retried")
    transitioned = await container.task_repo.transition(
        task.id,
        TaskStatus.FAILED.value,
        TaskStatus.RETRYING.value,
    )
    if not transitioned:
        raise HTTPException(status_code=409, detail="Failed to mark task as retrying")
    transitioned = await container.task_repo.transition(
        task.id,
        TaskStatus.RETRYING.value,
        TaskStatus.QUEUED.value,
        error_message=None,
        finished_at=None,
        started_at=None,
        cancellation_requested=False,
    )
    if not transitioned:
        raise HTTPException(status_code=409, detail="Failed to requeue task")
    await container.event_publisher.publish(
        "task.retrying",
        task_id=task.id,
        session_id=task.session_id,
        branch_id=task.branch_id,
    )
    await container.queue.enqueue(task.id, priority=task.priority)
    return {"task_id": task.id, "status": TaskStatus.QUEUED}


@router.get("/api/artifacts/{artifact_id}", response_model=ArtifactResponse)
async def get_artifact(artifact_id: str):
    container = get_container()
    artifact = await container.artifact_repo.get(artifact_id)
    if artifact is None:
        raise HTTPException(status_code=404, detail="Artifact not found")
    return _artifact_response(artifact)


@router.get("/api/scene-artifacts/{scene_artifact_id}", response_model=SceneArtifactResponse)
async def get_scene_artifact(scene_artifact_id: str):
    container = get_container()
    scene_artifact = await container.artifact_repo.get_scene_artifact(scene_artifact_id)
    if scene_artifact is None:
        raise HTTPException(status_code=404, detail="Scene artifact not found")
    return _scene_artifact_response(scene_artifact)


@router.get("/api/branches/{branch_id}/artifacts")
async def list_branch_artifacts(branch_id: str):
    container = get_container()
    branch = await container.branch_repo.get(branch_id)
    if branch is None:
        raise HTTPException(status_code=404, detail="Branch not found")
    artifacts = await container.artifact_repo.list_by_branch(branch_id)
    return {"items": [_artifact_response(item).model_dump(mode="json") for item in artifacts]}


@router.post("/api/artifacts/{artifact_id}/branch", response_model=BranchResponse)
async def branch_from_artifact(artifact_id: str):
    container = get_container()
    artifact = await container.artifact_repo.get(artifact_id)
    if artifact is None:
        raise HTTPException(status_code=404, detail="Artifact not found")
    source_branch = await container.branch_repo.get(artifact.branch_id)
    branch = BranchRecord(
        session_id=artifact.session_id,
        parent_branch_id=artifact.branch_id,
        base_artifact_id=artifact.id,
        head_artifact_id=artifact.id,
        name="branch-from-artifact",
    )
    await container.branch_repo.create(branch)
    if source_branch is not None:
        await container.session_repo.set_current_branch(artifact.session_id, branch.id)
    return BranchResponse(
        branch_id=branch.id,
        session_id=branch.session_id,
        parent_branch_id=branch.parent_branch_id,
        base_artifact_id=branch.base_artifact_id,
        head_artifact_id=branch.head_artifact_id,
        version=branch.version,
    )


@router.get("/api/workflows")
async def list_workflows():
    from workflow.runtime import WORKFLOW_NAMES

    logger.debug("Listing workflows")
    return {"items": list(WORKFLOW_NAMES)}


@router.get("/api/workflows/{workflow_name}/history")
async def workflow_history(workflow_name: str, thread_id: str, limit: int = 20):
    from services.workflow_service import build_run_config, resolve_workflow, serialize_snapshot

    workflow = resolve_workflow(workflow_name)
    logger.info(
        "Fetching workflow history workflow=%s thread_id=%s limit=%s",
        workflow_name,
        thread_id,
        limit,
    )
    snapshots = workflow.get_state_history(build_run_config(thread_id), limit=limit)
    return {
        "workflow": workflow_name,
        "thread_id": thread_id,
        "items": [serialize_snapshot(snapshot) for snapshot in snapshots],
    }


@router.post("/api/workflows/{workflow_name}/replay_sse")
async def workflow_replay_sse(workflow_name: str, req: ReplayRequest):
    from services.workflow_service import (
        build_run_config,
        find_snapshot,
        resolve_workflow,
        stream_workflow_response,
    )

    workflow = resolve_workflow(workflow_name)
    find_snapshot(workflow, req.thread_id, req.checkpoint_id)
    run_config = build_run_config(req.thread_id, req.checkpoint_id)
    logger.info(
        "Replay workflow requested workflow=%s thread_id=%s checkpoint_id=%s",
        workflow_name,
        req.thread_id,
        req.checkpoint_id,
    )
    return StreamingResponse(
        stream_workflow_response(workflow_name, None, run_config),
        media_type="text/event-stream",
    )


@router.post("/api/workflows/{workflow_name}/fork_sse")
async def workflow_fork_sse(workflow_name: str, req: ForkRequest):
    from services.workflow_service import find_snapshot, resolve_workflow, stream_workflow_response

    workflow = resolve_workflow(workflow_name)
    snapshot = find_snapshot(workflow, req.thread_id, req.checkpoint_id)

    if req.values is None and req.as_node is None:
        logger.info(
            "Fork workflow continue-from-checkpoint workflow=%s thread_id=%s checkpoint_id=%s",
            workflow_name,
            req.thread_id,
            req.checkpoint_id,
        )
        run_config = snapshot.config
    else:
        try:
            logger.info(
                "Fork workflow update-state workflow=%s thread_id=%s checkpoint_id=%s as_node=%s",
                workflow_name,
                req.thread_id,
                req.checkpoint_id,
                req.as_node,
            )
            run_config = workflow.update_state(
                snapshot.config,
                req.values or {},
                as_node=req.as_node,
            )
        except Exception as exc:
            logger.exception(
                "Failed to fork workflow workflow=%s thread_id=%s checkpoint_id=%s",
                workflow_name,
                req.thread_id,
                req.checkpoint_id,
            )
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    return StreamingResponse(
        stream_workflow_response(workflow_name, None, run_config),
        media_type="text/event-stream",
    )


@router.post("/api/workflows/animation/regenerate_scene_sse")
async def regenerate_scene_sse(req: RegenerateSceneRequest):
    from services.scene_service import clear_scene_coder_cache, update_director_scenes
    from services.workflow_service import build_run_config, resolve_workflow, stream_workflow_response

    workflow = resolve_workflow("animation")
    state_config = build_run_config(req.thread_id)

    try:
        logger.info(
            "Regenerate scene requested thread_id=%s scene_id=%s",
            req.thread_id,
            req.scene_id,
        )
        current_state = workflow.get_state(state_config)
        director_result = current_state.values.get("director")
        if not director_result:
            raise ValueError("No director result found in state")

        updated_director_result, target_scene = update_director_scenes(
            director_result=director_result,
            scene_id=req.scene_id,
            script=req.script,
            visual_design=req.visual_design,
        )

        clear_scene_coder_cache(target_scene, current_state.values.get("visual_architect"))

        next_config = workflow.update_state(
            state_config,
            {
                "director": updated_director_result,
                "last_action": f"编辑: 分镜 {req.scene_id}",
            },
            as_node="visual_architect_node",
        )
    except Exception as exc:
        logger.exception(
            "Regenerate scene failed thread_id=%s scene_id=%s",
            req.thread_id,
            req.scene_id,
        )
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return StreamingResponse(
        stream_workflow_response("animation", None, next_config),
        media_type="text/event-stream",
    )


@router.post("/api/generate_script_sse")
async def generate_script_sse(req: GenerateRequest):
    from services.workflow_service import (
        build_conversational_initial_state,
        build_run_config,
        stream_workflow_response,
    )

    thread_id = req.thread_id or str(uuid.uuid4())
    logger.info("Generate script requested thread_id=%s", thread_id)
    return StreamingResponse(
        stream_workflow_response(
            "conversational_tone",
            build_conversational_initial_state(req.source_text),
            build_run_config(thread_id),
        ),
        media_type="text/event-stream",
    )


@router.post("/api/generate_animation_sse")
async def generate_animation_sse(req: GenerateRequest):
    container = get_container()
    session = SessionRecord(
        title="Legacy animation generation",
        source_type="text",
        source_content=req.source_text,
    )
    await container.session_repo.create(session)
    branch = BranchRecord(session_id=session.id)
    await container.branch_repo.create(branch)
    await container.session_repo.set_current_branch(session.id, branch.id)
    source_artifact = await container.artifact_service.publish_artifact(
        session_id=session.id,
        branch_id=branch.id,
        task_id=None,
        artifact_type=ArtifactType.SOURCE_DOCUMENT,
        content_text=req.source_text,
        content_json={"source_type": "text"},
        summary="Legacy 源文档",
        publish_event=False,
    )
    task = TaskRecord(
        id=req.thread_id or str(uuid.uuid4()),
        session_id=session.id,
        branch_id=branch.id,
        task_type=TaskType.CREATE_VIDEO,
        request_payload={"source_artifact_id": source_artifact.id},
    )
    await container.task_repo.create(task)
    await container.event_publisher.publish(
        "task.created",
        task_id=task.id,
        session_id=task.session_id,
        branch_id=task.branch_id,
        payload={"task_type": task.task_type.value},
    )
    await container.task_repo.transition(
        task.id,
        TaskStatus.PENDING.value,
        TaskStatus.QUEUED.value,
    )
    await container.event_publisher.publish(
        "task.queued",
        task_id=task.id,
        session_id=task.session_id,
        branch_id=task.branch_id,
        payload={"task_type": task.task_type.value},
    )
    await container.queue.enqueue(task.id, priority=task.priority)
    logger.info("Generate animation requested task_id=%s", task.id)
    return StreamingResponse(
        _stream_legacy_task_events(task.id),
        media_type="text/event-stream",
    )
