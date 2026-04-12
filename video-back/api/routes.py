import uuid

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from api.schemas import ForkRequest, GenerateRequest, RegenerateSceneRequest, ReplayRequest
from services.scene_service import clear_scene_coder_cache, update_director_scenes
from services.workflow_service import (
    WORKFLOW_NAMES,
    build_animation_initial_state,
    build_conversational_initial_state,
    build_run_config,
    find_snapshot,
    resolve_workflow,
    serialize_snapshot,
    stream_workflow_response,
)
from utils.logger import get_logger

router = APIRouter()
logger = get_logger(__name__)


@router.get("/api/workflows")
async def list_workflows():
    logger.debug("Listing workflows")
    return {"items": list(WORKFLOW_NAMES)}


@router.get("/api/workflows/{workflow_name}/history")
async def workflow_history(workflow_name: str, thread_id: str, limit: int = 20):
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
    thread_id = req.thread_id or str(uuid.uuid4())
    logger.info("Generate animation requested thread_id=%s", thread_id)
    return StreamingResponse(
        stream_workflow_response(
            "animation",
            build_animation_initial_state(req.source_text),
            build_run_config(thread_id),
        ),
        media_type="text/event-stream",
    )
