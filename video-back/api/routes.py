import uuid

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from api.schemas import ForkRequest, GenerateRequest, PatchRequest, RecompileRequest, RegenerateSceneRequest, ReplayRequest
from services.scene_service import apply_scene_patch, prepare_scene_recompile
from services.workflow_service import (
    WORKFLOW_NAMES,
    build_animation_initial_state,
    build_conversational_initial_state,
    build_run_config,
    find_snapshot,
    resolve_workflow,
    serialize_snapshot,
    stream_video_pipeline_response,
    stream_workflow_response,
)
from utils.logger import get_logger

router = APIRouter()
logger = get_logger(__name__)


@router.get("/api/workflows")
async def list_workflows():
    return {"items": list(WORKFLOW_NAMES)}


@router.get("/api/workflows/{workflow_name}/history")
async def workflow_history(workflow_name: str, thread_id: str, limit: int = 20):
    workflow = resolve_workflow(workflow_name)
    snapshots = workflow.get_state_history(build_run_config(thread_id), limit=limit)
    return {
        "workflow": workflow_name,
        "thread_id": thread_id,
        "items": [serialize_snapshot(snapshot) for snapshot in snapshots],
    }


@router.get("/api/workflows/animation/state")
async def get_animation_state(thread_id: str):
    workflow = resolve_workflow("animation")
    try:
        state = workflow.get_state(build_run_config(thread_id))
        return {"thread_id": thread_id, "state": state.values}
    except Exception as exc:
        raise HTTPException(status_code=404, detail="State not found") from exc


@router.post("/api/workflows/{workflow_name}/replay_sse")
async def workflow_replay_sse(workflow_name: str, req: ReplayRequest):
    workflow = resolve_workflow(workflow_name)
    find_snapshot(workflow, req.thread_id, req.checkpoint_id)
    return StreamingResponse(
        stream_workflow_response(workflow_name, None, build_run_config(req.thread_id, req.checkpoint_id)),
        media_type="text/event-stream",
    )


@router.post("/api/workflows/{workflow_name}/fork_sse")
async def workflow_fork_sse(workflow_name: str, req: ForkRequest):
    workflow = resolve_workflow(workflow_name)
    snapshot = find_snapshot(workflow, req.thread_id, req.checkpoint_id)
    try:
        run_config = (
            snapshot.config
            if req.values is None and req.as_node is None
            else workflow.update_state(snapshot.config, req.values or {}, as_node=req.as_node)
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return StreamingResponse(
        stream_workflow_response(workflow_name, None, run_config),
        media_type="text/event-stream",
    )


@router.post("/api/generate_script_sse")
async def generate_script_sse(req: GenerateRequest):
    thread_id = req.thread_id or str(uuid.uuid4())
    source_text = req.source_text or req.oral_script or ""
    return StreamingResponse(
        stream_workflow_response(
            "conversational_tone",
            build_conversational_initial_state(source_text),
            build_run_config(thread_id),
        ),
        media_type="text/event-stream",
    )


@router.post("/api/generate_animation_sse")
async def generate_animation_sse(req: GenerateRequest):
    thread_id = req.thread_id or str(uuid.uuid4())
    oral_script = req.oral_script or req.source_text or ""
    return StreamingResponse(
        stream_workflow_response(
            "animation",
            build_animation_initial_state(oral_script),
            build_run_config(thread_id),
        ),
        media_type="text/event-stream",
    )


@router.post("/api/generate_video_pipeline_sse")
async def generate_video_pipeline_sse(req: GenerateRequest):
    thread_id = req.thread_id or str(uuid.uuid4())
    source_text = req.source_text or req.oral_script or ""
    return StreamingResponse(
        stream_video_pipeline_response(source_text, thread_id),
        media_type="text/event-stream",
    )


@router.post("/api/workflows/animation/regenerate_scene_sse")
async def regenerate_scene_sse(req: RegenerateSceneRequest):
    workflow = resolve_workflow("animation")
    run_config = build_run_config(req.thread_id)
    try:
        current_state = workflow.get_state(run_config).values
        updated_values, as_node = prepare_scene_recompile(
            current_state=current_state,
            scene_id=req.scene_id,
            oral_script=req.oral_script,
            recompile_from=req.recompile_from,
        )
        next_config = workflow.update_state(run_config, updated_values, as_node=as_node)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return StreamingResponse(
        stream_workflow_response("animation", None, next_config),
        media_type="text/event-stream",
    )


@router.post("/api/workflows/animation/recompile_layout_sse")
async def recompile_layout_sse(req: RecompileRequest):
    workflow = resolve_workflow("animation")
    run_config = build_run_config(req.thread_id)
    try:
        current_state = workflow.get_state(run_config).values
        updated_values, as_node = prepare_scene_recompile(
            current_state=current_state,
            scene_id=req.scene_id,
            oral_script=None,
            recompile_from=req.recompile_from,
        )
        next_config = workflow.update_state(run_config, updated_values, as_node=as_node)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return StreamingResponse(
        stream_workflow_response("animation", None, next_config),
        media_type="text/event-stream",
    )


@router.post("/api/workflows/animation/apply_patch_sse")
async def apply_patch_sse(req: PatchRequest):
    workflow = resolve_workflow("animation")
    run_config = build_run_config(req.thread_id)
    try:
        current_state = workflow.get_state(run_config).values
        updated_values, as_node = apply_scene_patch(current_state=current_state, scene_id=req.scene_id, patch=req.patch)
        next_config = workflow.update_state(run_config, updated_values, as_node=as_node)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return StreamingResponse(
        stream_workflow_response("animation", None, next_config),
        media_type="text/event-stream",
    )
