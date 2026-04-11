import asyncio
import json
import time
import uuid
from typing import Any, AsyncIterator

from fastapi import FastAPI, HTTPException
from fastapi.encoders import jsonable_encoder
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from utils.logger import log_event
from workflow.runtime import WORKFLOW_NAMES, get_workflow

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class GenerateRequest(BaseModel):
    source_text: str
    thread_id: str | None = None


class ReplayRequest(BaseModel):
    thread_id: str
    checkpoint_id: str


class ForkRequest(BaseModel):
    thread_id: str
    checkpoint_id: str
    values: dict[str, Any] | None = None
    as_node: str | None = None


def sse_data(payload: dict[str, Any]) -> str:
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"


def resolve_workflow(workflow_name: str):
    try:
        return get_workflow(workflow_name)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


def build_run_config(thread_id: str, checkpoint_id: str | None = None) -> dict[str, Any]:
    configurable: dict[str, Any] = {"thread_id": thread_id}
    if checkpoint_id:
        configurable["checkpoint_id"] = checkpoint_id
    return {"configurable": configurable}


def get_latest_checkpoint_id(workflow: Any, thread_id: str) -> str | None:
    try:
        state = workflow.get_state(build_run_config(thread_id))
    except Exception:
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
    config = build_run_config(thread_id)
    for snapshot in workflow.get_state_history(config):
        current_checkpoint_id = snapshot.config.get("configurable", {}).get("checkpoint_id")
        if current_checkpoint_id == checkpoint_id:
            return snapshot
    raise HTTPException(status_code=404, detail="Checkpoint not found")


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

    yield {
        "type": "setup",
        "request_id": request_id,
        "workflow": workflow_name,
        "thread_id": thread_id,
        "checkpoint_id": start_checkpoint_id,
    }

    try:
        async for chunk in workflow.astream(
            initial_state,
            config=run_config,
            stream_mode="updates",
            version="v2",
        ):
            yield {
                "type": "updates",
                "request_id": request_id,
                "workflow": workflow_name,
                "thread_id": thread_id,
                "data": jsonable_encoder(chunk),
            }
    except AttributeError:
        try:
            for chunk in workflow.stream(
                initial_state,
                config=run_config,
                stream_mode="updates",
                version="v2",
            ):
                yield {
                    "type": "updates",
                    "request_id": request_id,
                    "workflow": workflow_name,
                    "thread_id": thread_id,
                    "data": jsonable_encoder(chunk),
                }
                await asyncio.sleep(0.01)
        except Exception as exc:
            yield {
                "type": "error",
                "request_id": request_id,
                "workflow": workflow_name,
                "thread_id": thread_id,
                "message": str(exc),
            }
    except Exception as exc:
        yield {
            "type": "error",
            "request_id": request_id,
            "workflow": workflow_name,
            "thread_id": thread_id,
            "message": str(exc),
        }
    finally:
        yield {
            "type": "end",
            "request_id": request_id,
            "workflow": workflow_name,
            "thread_id": thread_id,
            "checkpoint_id": get_latest_checkpoint_id(workflow, thread_id) if thread_id else None,
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

    try:
        async for payload in stream_graph_updates(
            workflow,
            initial_state,
            request_id,
            workflow_name,
            run_config,
        ):
            has_error = has_error or payload["type"] == "error"
            yield sse_data(payload)
        log_event(
            request_id=request_id,
            workflow=workflow_name,
            node="workflow",
            status="error" if has_error else "success",
            latency_ms=int((time.perf_counter() - start) * 1000),
            thread_id=run_config.get("configurable", {}).get("thread_id"),
            checkpoint_id=get_latest_checkpoint_id(
                workflow, run_config.get("configurable", {}).get("thread_id")
            ),
        )
    except Exception as exc:
        log_event(
            request_id=request_id,
            workflow=workflow_name,
            node="workflow",
            status="error",
            latency_ms=int((time.perf_counter() - start) * 1000),
            message=str(exc),
            thread_id=run_config.get("configurable", {}).get("thread_id"),
        )
        raise


def build_conversational_initial_state(source_text: str) -> dict[str, Any]:
    return {
        "oral_content": source_text,
        "current_script": "",
        "review_score": None,
        "last_feedback": None,
        "loop_count": 0,
    }


def build_animation_initial_state(source_text: str) -> dict[str, Any]:
    return {
        "script": source_text,
        "director": None,
        "visual_architect": None,
        "coder": [],
        "failed_scenes": [],
        "max_parallel_coders": 4,
    }


@app.get("/api/workflows")
async def list_workflows():
    return {"items": list(WORKFLOW_NAMES)}


@app.get("/api/workflows/{workflow_name}/history")
async def workflow_history(workflow_name: str, thread_id: str, limit: int = 20):
    workflow = resolve_workflow(workflow_name)
    snapshots = workflow.get_state_history(build_run_config(thread_id), limit=limit)
    return {
        "workflow": workflow_name,
        "thread_id": thread_id,
        "items": [serialize_snapshot(snapshot) for snapshot in snapshots],
    }


@app.post("/api/workflows/{workflow_name}/replay_sse")
async def workflow_replay_sse(workflow_name: str, req: ReplayRequest):
    workflow = resolve_workflow(workflow_name)
    _ = find_snapshot(workflow, req.thread_id, req.checkpoint_id)
    run_config = build_run_config(req.thread_id, req.checkpoint_id)
    return StreamingResponse(
        stream_workflow_response(workflow_name, None, run_config),
        media_type="text/event-stream",
    )


@app.post("/api/workflows/{workflow_name}/fork_sse")
async def workflow_fork_sse(workflow_name: str, req: ForkRequest):
    workflow = resolve_workflow(workflow_name)
    snapshot = find_snapshot(workflow, req.thread_id, req.checkpoint_id)
    try:
        next_config = workflow.update_state(
            snapshot.config,
            req.values,
            as_node=req.as_node,
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return StreamingResponse(
        stream_workflow_response(workflow_name, None, next_config),
        media_type="text/event-stream",
    )


@app.post("/api/generate_script_sse")
async def generate_script_sse(req: GenerateRequest):
    thread_id = req.thread_id or str(uuid.uuid4())
    run_config = build_run_config(thread_id)
    initial_state = build_conversational_initial_state(req.source_text)
    return StreamingResponse(
        stream_workflow_response("conversational_tone", initial_state, run_config),
        media_type="text/event-stream",
    )


@app.post("/api/generate_animation_sse")
async def generate_animation_sse(req: GenerateRequest):
    thread_id = req.thread_id or str(uuid.uuid4())
    run_config = build_run_config(thread_id)
    initial_state = build_animation_initial_state(req.source_text)
    return StreamingResponse(
        stream_workflow_response("animation", initial_state, run_config),
        media_type="text/event-stream",
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
