import asyncio
import json
import time
import uuid
from typing import Any, AsyncIterator, Iterator

from fastapi import HTTPException
from fastapi.encoders import jsonable_encoder

from utils.logger import get_logger, log_event
from workflow.runtime import WORKFLOW_NAMES, get_workflow

logger = get_logger(__name__)

WORKFLOW_STAGE_PLANS: dict[str, list[dict[str, Any]]] = {
    "conversational_tone": [
        {
            "node_key": "content_writer",
            "label": "正在改写口播稿",
            "description": "把原文改写成更适合短视频讲述的口播表达。",
            "estimate_seconds": 25,
        },
        {
            "node_key": "content_reviewer",
            "label": "正在评估口播质量",
            "description": "检查节奏、清晰度和可讲述性，必要时会继续优化。",
            "estimate_seconds": 15,
        },
    ],
    "animation": [
        {
            "node_key": "director_node",
            "label": "正在拆分镜头",
            "description": "把口播稿拆成短视频镜头段落，并估算每段时长。",
            "estimate_seconds": 30,
        },
        {
            "node_key": "visual_architect_node",
            "label": "正在设计视觉方案",
            "description": "规划画面安全区、元素布局、主题色和动画节奏。",
            "estimate_seconds": 35,
        },
        {
            "node_key": "coder_node",
            "label": "正在生成镜头代码",
            "description": "把每个镜头方案转换成可预览的 Remotion 代码。",
            "estimate_seconds": 90,
        },
    ],
}


def get_stage_plan(workflow_name: str) -> list[dict[str, Any]]:
    return WORKFLOW_STAGE_PLANS.get(workflow_name, [])


def estimate_total_seconds(workflow_name: str, initial_state: dict[str, Any] | None) -> int:
    base_total = sum(stage["estimate_seconds"] for stage in get_stage_plan(workflow_name))
    source = ""
    if initial_state:
        source = str(initial_state.get("script") or initial_state.get("oral_content") or "")

    if workflow_name == "animation":
        # Coder work scales with the script length because longer scripts usually produce more scenes.
        estimated_scene_count = max(2, min(8, round(len(source) / 80) or 2))
        return 30 + 35 + estimated_scene_count * 25

    if workflow_name == "conversational_tone":
        estimated_loops = 1 if len(source) < 500 else 2
        return max(base_total, estimated_loops * base_total)

    return max(base_total, 30)


def extract_update_node(chunk: Any) -> tuple[str | None, Any | None]:
    if not isinstance(chunk, dict) or not chunk:
        return None, None
    node_name = next(iter(chunk.keys()))
    return node_name, chunk.get(node_name)


def build_progress_payload(
    workflow_name: str,
    request_id: str,
    thread_id: str | None,
    start_checkpoint_id: str | None,
    started_at: float,
    estimated_total_seconds: int,
    node_key: str | None,
    status: str,
    completed_count: int,
    message: str | None = None,
    detail: dict[str, Any] | None = None,
) -> dict[str, Any]:
    stage_plan = get_stage_plan(workflow_name)
    stage_by_key = {stage["node_key"]: stage for stage in stage_plan}
    current_stage = stage_by_key.get(node_key or "") or (stage_plan[0] if stage_plan else {})
    total_count = max(1, len(stage_plan))
    elapsed_seconds = max(0, int(time.perf_counter() - started_at))
    percent = min(100, max(0, round((completed_count / total_count) * 100)))
    if status == "running" and completed_count == 0:
        percent = max(percent, 3)
    if status == "running":
        percent = min(percent, 95)
    if status == "success":
        percent = 100

    eta_seconds = None
    if status == "running":
        eta_seconds = max(0, estimated_total_seconds - elapsed_seconds)

    return {
        "type": "progress",
        "request_id": request_id,
        "workflow": workflow_name,
        "thread_id": thread_id,
        "checkpoint_id": start_checkpoint_id,
        "progress": {
            "status": status,
            "node_key": node_key,
            "node_label": current_stage.get("label") or message or "处理中",
            "description": message or current_stage.get("description") or "系统正在处理当前阶段。",
            "completed_count": completed_count,
            "total_count": total_count,
            "percent": percent,
            "elapsed_seconds": elapsed_seconds,
            "eta_seconds": eta_seconds,
            "estimated_total_seconds": estimated_total_seconds,
            "detail": detail or {},
        },
    }


def next_stage_key(workflow_name: str, completed_node_key: str | None) -> str | None:
    stage_plan = get_stage_plan(workflow_name)
    keys = [stage["node_key"] for stage in stage_plan]
    if not keys:
        return None
    if completed_node_key not in keys:
        return keys[0]
    next_index = keys.index(completed_node_key) + 1
    if next_index >= len(keys):
        return completed_node_key
    return keys[next_index]


def sse_data(payload: dict[str, Any]) -> str:
    return f"data: {json.dumps(payload, ensure_ascii=False, default=str)}\n\n"


def resolve_workflow(workflow_name: str) -> Any:
    try:
        workflow = get_workflow(workflow_name)
        logger.debug("Resolved workflow=%s", workflow_name)
        return workflow
    except KeyError as exc:
        logger.warning("Unknown workflow requested workflow=%s", workflow_name)
        raise HTTPException(status_code=404, detail=str(exc)) from exc


def build_run_config(thread_id: str, checkpoint_id: str | None = None) -> dict[str, Any]:
    configurable: dict[str, Any] = {"thread_id": thread_id}
    if checkpoint_id:
        configurable["checkpoint_id"] = checkpoint_id
    return {"configurable": configurable}


def get_latest_checkpoint_id(workflow: Any, thread_id: str | None) -> str | None:
    if not thread_id:
        return None
    try:
        state = workflow.get_state(build_run_config(thread_id))
    except Exception:
        logger.exception("Failed to fetch latest checkpoint thread_id=%s", thread_id)
        return None
    return state.config.get("configurable", {}).get("checkpoint_id")


def serialize_task(task: Any) -> dict[str, Any]:
    return {
        "id": getattr(task, "id", None),
        "name": getattr(task, "name", None),
        "path": list(getattr(task, "path", ()) or ()),
        "error": str(getattr(task, "error", None)) if getattr(task, "error", None) else None,
        "interrupts": jsonable_encoder(getattr(task, "interrupts", ()) or ()),
        "result": jsonable_encoder(getattr(task, "result", None)),
    }


def serialize_snapshot(snapshot: Any) -> dict[str, Any]:
    config = getattr(snapshot, "config", {}) or {}
    configurable = config.get("configurable", {})
    parent_config = getattr(snapshot, "parent_config", None) or {}
    parent_configurable = parent_config.get("configurable", {}) if parent_config else {}
    metadata = getattr(snapshot, "metadata", {}) or {}

    return {
        "checkpoint_id": configurable.get("checkpoint_id"),
        "thread_id": configurable.get("thread_id"),
        "checkpoint_ns": configurable.get("checkpoint_ns", ""),
        "parent_checkpoint_id": parent_configurable.get("checkpoint_id"),
        "created_at": getattr(snapshot, "created_at", None),
        "next_nodes": list(getattr(snapshot, "next", ()) or ()),
        "values": jsonable_encoder(getattr(snapshot, "values", {})),
        "metadata": jsonable_encoder(metadata),
        "step": metadata.get("step"),
        "source": metadata.get("source"),
        "tasks": [serialize_task(task) for task in (getattr(snapshot, "tasks", ()) or ())],
    }


def find_snapshot(workflow: Any, thread_id: str, checkpoint_id: str) -> Any:
    for snapshot in workflow.get_state_history(build_run_config(thread_id)):
        current_checkpoint_id = snapshot.config.get("configurable", {}).get("checkpoint_id")
        if current_checkpoint_id == checkpoint_id:
            return snapshot
    logger.warning(
        "Checkpoint not found workflow_snapshot_search thread_id=%s checkpoint_id=%s",
        thread_id,
        checkpoint_id,
    )
    raise HTTPException(status_code=404, detail="Checkpoint not found")


async def _stream_from_sync_iterator(iterator: Iterator[Any]) -> AsyncIterator[Any]:
    for chunk in iterator:
        yield chunk
        await asyncio.sleep(0.01)


async def iterate_workflow_updates(
    workflow: Any,
    initial_state: dict[str, Any] | None,
    run_config: dict[str, Any],
) -> AsyncIterator[Any]:
    stream_kwargs = {
        "config": run_config,
        "stream_mode": "updates",
        "version": "v2",
    }
    if hasattr(workflow, "astream"):
        async for chunk in workflow.astream(initial_state, **stream_kwargs):
            yield chunk
        return

    if hasattr(workflow, "stream"):
        async for chunk in _stream_from_sync_iterator(workflow.stream(initial_state, **stream_kwargs)):
            yield chunk
        return

    raise RuntimeError("Workflow does not support streaming")


async def stream_graph_updates(
    workflow: Any,
    initial_state: dict[str, Any] | None,
    request_id: str,
    workflow_name: str,
    run_config: dict[str, Any],
) -> AsyncIterator[dict[str, Any]]:
    configurable = run_config.get("configurable", {})
    thread_id = configurable.get("thread_id")
    start_checkpoint_id = configurable.get("checkpoint_id")
    started_at = time.perf_counter()
    estimated_total_seconds = estimate_total_seconds(workflow_name, initial_state)
    completed_nodes: set[str] = set()
    first_stage_key = next_stage_key(workflow_name, None)

    logger.info(
        "Streaming workflow start request_id=%s workflow=%s thread_id=%s checkpoint_id=%s",
        request_id,
        workflow_name,
        thread_id,
        start_checkpoint_id,
    )
    yield {
        "type": "setup",
        "request_id": request_id,
        "workflow": workflow_name,
        "thread_id": thread_id,
        "checkpoint_id": start_checkpoint_id,
        "progress": build_progress_payload(
            workflow_name=workflow_name,
            request_id=request_id,
            thread_id=thread_id,
            start_checkpoint_id=start_checkpoint_id,
            started_at=started_at,
            estimated_total_seconds=estimated_total_seconds,
            node_key=first_stage_key,
            status="running",
            completed_count=0,
        )["progress"],
    }
    yield build_progress_payload(
        workflow_name=workflow_name,
        request_id=request_id,
        thread_id=thread_id,
        start_checkpoint_id=start_checkpoint_id,
        started_at=started_at,
        estimated_total_seconds=estimated_total_seconds,
        node_key=first_stage_key,
        status="running",
        completed_count=0,
    )

    try:
        async for chunk in iterate_workflow_updates(workflow, initial_state, run_config):
            node_name, node_data = extract_update_node(chunk)
            if node_name:
                completed_nodes.add(node_name)
            completed_count = min(len(completed_nodes), max(1, len(get_stage_plan(workflow_name))))
            progress = build_progress_payload(
                workflow_name=workflow_name,
                request_id=request_id,
                thread_id=thread_id,
                start_checkpoint_id=start_checkpoint_id,
                started_at=started_at,
                estimated_total_seconds=estimated_total_seconds,
                node_key=next_stage_key(workflow_name, node_name),
                status="running",
                completed_count=completed_count,
                detail={
                    "completed_node": node_name,
                    "last_action": node_data.get("last_action") if isinstance(node_data, dict) else None,
                },
            )["progress"]
            logger.debug(
                "Workflow update request_id=%s workflow=%s thread_id=%s",
                request_id,
                workflow_name,
                thread_id,
            )
            yield {
                "type": "updates",
                "request_id": request_id,
                "workflow": workflow_name,
                "thread_id": thread_id,
                "data": jsonable_encoder(chunk),
                "progress": progress,
            }
            if progress["status"] == "running":
                yield {
                    "type": "progress",
                    "request_id": request_id,
                    "workflow": workflow_name,
                    "thread_id": thread_id,
                    "checkpoint_id": start_checkpoint_id,
                    "progress": progress,
                }
    except Exception as exc:
        logger.exception(
            "Workflow stream failed request_id=%s workflow=%s thread_id=%s",
            request_id,
            workflow_name,
            thread_id,
        )
        yield {
            "type": "error",
            "request_id": request_id,
            "workflow": workflow_name,
            "thread_id": thread_id,
            "message": str(exc),
            "progress": build_progress_payload(
                workflow_name=workflow_name,
                request_id=request_id,
                thread_id=thread_id,
                start_checkpoint_id=start_checkpoint_id,
                started_at=started_at,
                estimated_total_seconds=estimated_total_seconds,
                node_key=next_stage_key(workflow_name, None),
                status="error",
                completed_count=len(completed_nodes),
                message=str(exc),
            )["progress"],
        }
    finally:
        latest_checkpoint_id = get_latest_checkpoint_id(workflow, thread_id)
        logger.info(
            "Streaming workflow end request_id=%s workflow=%s thread_id=%s checkpoint_id=%s",
            request_id,
            workflow_name,
            thread_id,
            latest_checkpoint_id,
        )
        yield {
            "type": "end",
            "request_id": request_id,
            "workflow": workflow_name,
            "thread_id": thread_id,
            "checkpoint_id": latest_checkpoint_id,
            "progress": build_progress_payload(
                workflow_name=workflow_name,
                request_id=request_id,
                thread_id=thread_id,
                start_checkpoint_id=latest_checkpoint_id,
                started_at=started_at,
                estimated_total_seconds=estimated_total_seconds,
                node_key=next_stage_key(workflow_name, None),
                status="success",
                completed_count=max(1, len(get_stage_plan(workflow_name))),
                message="工作流已完成。",
            )["progress"],
        }


async def stream_workflow_response(
    workflow_name: str,
    initial_state: dict[str, Any] | None,
    run_config: dict[str, Any],
) -> AsyncIterator[str]:
    workflow = resolve_workflow(workflow_name)
    request_id = str(uuid.uuid4())
    start = time.perf_counter()
    has_error = False
    thread_id = run_config.get("configurable", {}).get("thread_id")

    try:
        async for payload in stream_graph_updates(
            workflow=workflow,
            initial_state=initial_state,
            request_id=request_id,
            workflow_name=workflow_name,
            run_config=run_config,
        ):
            has_error = has_error or payload["type"] == "error"
            yield sse_data(payload)
    except Exception as exc:
        logger.exception(
            "Workflow response failed request_id=%s workflow=%s thread_id=%s",
            request_id,
            workflow_name,
            thread_id,
        )
        log_event(
            level="error",
            request_id=request_id,
            workflow=workflow_name,
            node="workflow",
            status="error",
            latency_ms=int((time.perf_counter() - start) * 1000),
            message=str(exc),
            thread_id=thread_id,
        )
        raise
    else:
        log_event(
            level="error" if has_error else "info",
            request_id=request_id,
            workflow=workflow_name,
            node="workflow",
            status="error" if has_error else "success",
            latency_ms=int((time.perf_counter() - start) * 1000),
            thread_id=thread_id,
            checkpoint_id=get_latest_checkpoint_id(workflow, thread_id),
        )


def build_conversational_initial_state(source_text: str) -> dict[str, Any]:
    return {
        "oral_content": source_text,
        "current_script": "",
        "review_score": None,
        "last_feedback": None,
        "loop_count": 0,
        "last_action": None,
    }


def build_animation_initial_state(source_text: str) -> dict[str, Any]:
    return {
        "script": source_text,
        "director": None,
        "visual_architect": None,
        "coder": [],
        "failed_scenes": [],
        "max_parallel_coders": 4,
        "last_action": None,
    }
