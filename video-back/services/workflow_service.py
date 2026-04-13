from __future__ import annotations

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
        {"node_key": "rewrite_oral_script_node", "label": "正在改写口语稿", "description": "把博文转成适合短视频讲述的口语稿。", "estimate_seconds": 20},
        {"node_key": "review_oral_script_node", "label": "正在评审口语稿", "description": "检查节奏、清晰度和可讲述性。", "estimate_seconds": 12},
        {"node_key": "finalize_oral_script_node", "label": "正在整理脚本段落", "description": "切分讲述段落并生成结构化脚本。", "estimate_seconds": 4},
    ],
    "animation": [
        {"node_key": "parse_oral_script_node", "label": "正在解析口语稿", "description": "把口语稿整理成可编译的讲述结构。", "estimate_seconds": 4},
        {"node_key": "plan_scenes_node", "label": "正在规划镜头", "description": "根据讲述节奏生成场景顺序与视觉目标。", "estimate_seconds": 4},
        {"node_key": "generate_marks_node", "label": "正在生成时间轴", "description": "统一生成全局与局部动画 marks。", "estimate_seconds": 3},
        {"node_key": "compile_layout_node", "label": "正在编译布局", "description": "为每个场景计算安全区内的布局盒模型。", "estimate_seconds": 3},
        {"node_key": "compile_motion_node", "label": "正在编译动效", "description": "按 marks 绑定场景动效和进场顺序。", "estimate_seconds": 3},
        {"node_key": "generate_dsl_node", "label": "正在生成 DSL", "description": "输出中间渲染语法树。", "estimate_seconds": 2},
        {"node_key": "generate_scene_code_node", "label": "正在生成代码", "description": "基于 DSL 模板化生成 Remotion 代码。", "estimate_seconds": 5},
        {"node_key": "validate_scene_node", "label": "正在校验结果", "description": "检查布局越界、引用错误和代码兼容性。", "estimate_seconds": 3},
        {"node_key": "repair_scene_node", "label": "正在自动修复", "description": "对可修复场景执行降级或修正。", "estimate_seconds": 3},
        {"node_key": "finalize_output_node", "label": "正在封装结果", "description": "整理最终场景、代码与校验输出。", "estimate_seconds": 1},
    ],
}


def get_stage_plan(workflow_name: str) -> list[dict[str, Any]]:
    return WORKFLOW_STAGE_PLANS.get(workflow_name, [])


def estimate_total_seconds(workflow_name: str, initial_state: dict[str, Any] | None) -> int:
    base_total = sum(stage["estimate_seconds"] for stage in get_stage_plan(workflow_name))
    source = ""
    if initial_state:
        source = str(initial_state.get("source_text") or initial_state.get("oral_script") or "")
    if workflow_name == "animation":
        estimated_scene_count = max(2, min(8, round(len(source) / 40) or 2))
        return max(base_total, 10 + estimated_scene_count * 6)
    return max(base_total, 20)


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
    if status == "running":
        percent = min(max(percent, 3), 95)
    elif status in {"success", "partial_success"}:
        percent = 100

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
            "eta_seconds": max(0, estimated_total_seconds - elapsed_seconds) if status == "running" else None,
            "estimated_total_seconds": estimated_total_seconds,
            "detail": detail or {},
        },
    }


def next_stage_key(workflow_name: str, completed_node_key: str | None) -> str | None:
    keys = [stage["node_key"] for stage in get_stage_plan(workflow_name)]
    if not keys:
        return None
    if completed_node_key not in keys:
        return keys[0]
    next_index = keys.index(completed_node_key) + 1
    return keys[min(next_index, len(keys) - 1)]


def sse_data(payload: dict[str, Any]) -> str:
    return f"data: {json.dumps(payload, ensure_ascii=False, default=str)}\n\n"


def resolve_workflow(workflow_name: str) -> Any:
    try:
        return get_workflow(workflow_name)
    except KeyError as exc:
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
    stream_kwargs = {"config": run_config, "stream_mode": "updates", "version": "v2"}
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
    had_error = False

    yield {
        "type": "setup",
        "request_id": request_id,
        "workflow": workflow_name,
        "thread_id": thread_id,
        "checkpoint_id": start_checkpoint_id,
        "progress": build_progress_payload(
            workflow_name,
            request_id,
            thread_id,
            start_checkpoint_id,
            started_at,
            estimated_total_seconds,
            first_stage_key,
            "running",
            0,
        )["progress"],
    }

    try:
        async for chunk in iterate_workflow_updates(workflow, initial_state, run_config):
            node_name, node_data = extract_update_node(chunk)
            if node_name:
                completed_nodes.add(node_name)
            completed_count = min(len(completed_nodes), max(1, len(get_stage_plan(workflow_name))))
            progress = build_progress_payload(
                workflow_name,
                request_id,
                thread_id,
                start_checkpoint_id,
                started_at,
                estimated_total_seconds,
                next_stage_key(workflow_name, node_name),
                "running",
                completed_count,
                detail={
                    "completed_node": node_name,
                    "last_action": node_data.get("last_action") if isinstance(node_data, dict) else None,
                },
            )["progress"]
            yield {
                "type": "updates",
                "request_id": request_id,
                "workflow": workflow_name,
                "thread_id": thread_id,
                "data": jsonable_encoder(chunk),
                "progress": progress,
            }
            yield {
                "type": "progress",
                "request_id": request_id,
                "workflow": workflow_name,
                "thread_id": thread_id,
                "checkpoint_id": start_checkpoint_id,
                "progress": progress,
            }
    except Exception as exc:
        had_error = True
        logger.exception("Workflow stream failed workflow=%s thread_id=%s", workflow_name, thread_id)
        yield {
            "type": "error",
            "request_id": request_id,
            "workflow": workflow_name,
            "thread_id": thread_id,
            "message": str(exc),
            "progress": build_progress_payload(
                workflow_name,
                request_id,
                thread_id,
                start_checkpoint_id,
                started_at,
                estimated_total_seconds,
                next_stage_key(workflow_name, None),
                "error",
                len(completed_nodes),
                message=str(exc),
            )["progress"],
        }
    finally:
        latest_checkpoint_id = get_latest_checkpoint_id(workflow, thread_id)
        final_state_values = {}
        try:
            if thread_id:
                final_state_values = workflow.get_state(build_run_config(thread_id)).values
        except Exception:
            logger.exception("Failed to read final state workflow=%s thread_id=%s", workflow_name, thread_id)

        failed_scenes = list(final_state_values.get("failed_scenes", []) or [])
        total_scenes = len(final_state_values.get("scenes", []) or [])
        if had_error:
            end_status = "error"
            end_message = "工作流执行失败。"
        elif failed_scenes and total_scenes and len(failed_scenes) < total_scenes:
            end_status = "partial_success"
            end_message = f"部分场景失败 ({len(failed_scenes)}/{total_scenes})，其余结果已保留。"
        elif failed_scenes and total_scenes:
            end_status = "error"
            end_message = "所有场景均失败。"
        else:
            end_status = "success"
            end_message = "工作流已完成。"

        yield {
            "type": "end",
            "request_id": request_id,
            "workflow": workflow_name,
            "thread_id": thread_id,
            "checkpoint_id": latest_checkpoint_id,
            "status": end_status,
            "progress": build_progress_payload(
                workflow_name,
                request_id,
                thread_id,
                latest_checkpoint_id,
                started_at,
                estimated_total_seconds,
                next_stage_key(workflow_name, None),
                end_status,
                max(1, len(get_stage_plan(workflow_name))),
                message=end_message,
                detail={"failed_scenes": failed_scenes, "total_scenes": total_scenes},
            )["progress"],
        }


async def stream_workflow_response(
    workflow_name: str,
    initial_state: dict[str, Any] | None,
    run_config: dict[str, Any],
) -> AsyncIterator[str]:
    workflow = resolve_workflow(workflow_name)
    request_id = str(uuid.uuid4())
    thread_id = run_config.get("configurable", {}).get("thread_id")
    start = time.perf_counter()
    has_error = False

    try:
        async for payload in stream_graph_updates(workflow, initial_state, request_id, workflow_name, run_config):
            has_error = has_error or payload["type"] == "error" or payload.get("status") == "error"
            yield sse_data(payload)
    except Exception as exc:
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


async def stream_video_pipeline_response(source_text: str, thread_id: str) -> AsyncIterator[str]:
    script_thread_id = f"{thread_id}:script"
    animation_thread_id = f"{thread_id}:animation"

    async for payload in stream_workflow_response(
        "conversational_tone",
        build_conversational_initial_state(source_text),
        build_run_config(script_thread_id),
    ):
        yield payload

    script_workflow = resolve_workflow("conversational_tone")
    script_state = script_workflow.get_state(build_run_config(script_thread_id)).values
    oral_script_result = script_state.get("oral_script_result") or {}
    oral_script = oral_script_result.get("oral_script") or script_state.get("current_script") or source_text

    async for payload in stream_workflow_response(
        "animation",
        build_animation_initial_state(oral_script, oral_script_result=oral_script_result),
        build_run_config(animation_thread_id),
    ):
        yield payload


def build_conversational_initial_state(source_text: str) -> dict[str, Any]:
    return {
        "source_text": source_text,
        "current_script": "",
        "review_score": None,
        "last_feedback": None,
        "loop_count": 0,
        "oral_script_result": None,
        "last_action": None,
    }


def build_animation_initial_state(oral_script: str, oral_script_result: dict[str, Any] | None = None) -> dict[str, Any]:
    return {
        "oral_script": oral_script,
        "oral_script_result": oral_script_result,
        "parsed_script": None,
        "scenes": [],
        "marks": None,
        "layouts": {},
        "motions": {},
        "dsl": {},
        "codes": {},
        "validations": {},
        "patches": {},
        "failed_scenes": [],
        "repairable_scenes": [],
        "theme_profile": None,
        "compile_config": {"fps": 30, "aspect_ratio": "9:16"},
        "regenerate_scene_id": None,
        "recompile_from": None,
        "last_action": None,
    }
