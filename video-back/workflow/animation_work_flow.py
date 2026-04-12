import operator
from typing import Annotated, List, TypedDict

from langchain_core.messages import HumanMessage
from langgraph.constants import END
from langgraph.graph import StateGraph
from langgraph.types import Send

from agents.coder import CoderResult
from agents.director import DirectorResult, Scene, director_agent, example as director_example
from agents.qa_guard import Result as QAResult
from agents.qa_guard import qa_guard_agent
from agents.visual_architect import (
    VisualProtocol,
    example as visual_architect_example,
    visual_architect_agent,
)
from prompts.manager import PromptManager
from utils.cache import SimpleCache, build_cache_key
from utils.logger import get_logger
from utils.structured_output import invoke_structured

coder_cache = SimpleCache()
director_cache = SimpleCache()
qa_cache = SimpleCache()
visual_architect_cache = SimpleCache()
logger = get_logger(__name__)


def reduce_last_action(left: str | None, right: str | list[str] | None) -> str | None:
    if not right:
        return left
    if isinstance(right, list):
        return right[-1]
    return right


class State(TypedDict):
    script: str
    director: DirectorResult | dict | None
    visual_architect: VisualProtocol | dict | None
    coder: Annotated[List[CoderResult], operator.add]
    failed_scenes: Annotated[List[str], operator.add]
    max_parallel_coders: int
    last_action: Annotated[str | None, reduce_last_action]


class CoderTaskState(TypedDict):
    scene: Scene | dict
    visual_architect: VisualProtocol | dict | None


def to_json_payload(value):
    import json

    if isinstance(value, dict):
        return json.dumps(value, ensure_ascii=False, default=str)
    if hasattr(value, "model_dump_json"):
        return value.model_dump_json()
    return json.dumps(value, ensure_ascii=False, default=str)


def to_state_payload(value):
    if value is None:
        return None
    if isinstance(value, dict):
        return value
    if hasattr(value, "model_dump"):
        return value.model_dump()
    return value


def scene_id_of(scene: Scene | dict | None) -> str:
    if scene is None:
        return "unknown-scene"
    if isinstance(scene, dict):
        return str(scene.get("scene_id", "unknown-scene"))
    return scene.scene_id


def qa_guard_check(result: CoderResult, prompt_manager: PromptManager) -> bool:
    logger.debug("Running QA guard for scene_id=%s", result.scene_id)
    messages = prompt_manager.get_langchain_messages(qa_guard_agent["prompt_name"])
    messages.append(
        HumanMessage(
            f"请检查以下代码是否可用。\n"
            f"scene_id: {result.scene_id}\n"
            f"code:\n{result.code}"
        )
    )

    cache_key = build_cache_key(qa_guard_agent["name"], result.scene_id, result.code)
    qa_result = qa_cache.get(cache_key, model_type=QAResult)
    if qa_result is None:
        qa_result = invoke_structured(
            model=qa_guard_agent["model"],
            schema=qa_guard_agent["response_format"],
            messages=messages,
            operation=f"qa_guard:{result.scene_id}",
        )
        qa_cache.set(cache_key, qa_result)

    passed = qa_result.status.strip().lower() != "fail"
    logger.info("QA guard finished scene_id=%s passed=%s", result.scene_id, passed)
    return passed


def director_node(state: State, prompt_manager: PromptManager) -> State:
    logger.info("Director node started")
    messages = prompt_manager.get_langchain_messages(
        director_agent["prompt_name"], example=director_example
    )
    messages.append(HumanMessage(f"请根据以下脚本生成分镜脚本：\n{state['script']}"))

    cache_key = build_cache_key(director_agent["name"], state["script"])
    result = director_cache.get(cache_key, model_type=DirectorResult)
    if result is None:
        try:
            result = invoke_structured(
                model=director_agent["model"],
                schema=director_agent["response_format"],
                messages=messages,
                operation="director",
            )
            if result is None:
                raise ValueError("Director agent returned None. Check model logs/quota.")
            director_cache.set(cache_key, result)
        except Exception:
            logger.exception("Director node failed")
            raise

    logger.info(
        "Director node finished art_direction=%s scene_count=%s",
        getattr(result, "art_direction", None),
        len(getattr(result, "scenes", []) or []),
    )
    return {
        "script": state["script"],
        "director": to_state_payload(result),
        "visual_architect": state["visual_architect"],
        "coder": [],
        "failed_scenes": [],
        "max_parallel_coders": state["max_parallel_coders"],
        "last_action": "生成全局分镜",
    }


def visual_architect_node(state: State, prompt_manager: PromptManager) -> State:
    logger.info("Visual architect node started")
    messages = prompt_manager.get_langchain_messages(
        visual_architect_agent["prompt_name"], example=visual_architect_example
    )
    messages.append(HumanMessage(f"请根据以下分镜脚本生成视觉设计：\n{state['director']}"))

    director_json = to_json_payload(state["director"])
    cache_key = build_cache_key(visual_architect_agent["name"], director_json)
    result = visual_architect_cache.get(cache_key, model_type=VisualProtocol)
    if result is None:
        result = invoke_structured(
            model=visual_architect_agent["model"],
            schema=visual_architect_agent["response_format"],
            messages=messages,
            operation="visual_architect",
        )
        if result is None:
            raise ValueError(
                "Visual Architect agent returned None. This might be due to a model error or structured output parsing failure."
            )
        visual_architect_cache.set(cache_key, result)

    visual_architect_payload = to_state_payload(result)
    logger.info(
        "Visual architect node finished layout_items=%s marks=%s",
        len(visual_architect_payload.get("layout_blueprint", [])) if isinstance(visual_architect_payload, dict) else 0,
        list(visual_architect_payload.get("marks_definition", {}).keys()) if isinstance(visual_architect_payload, dict) else [],
    )
    return {
        "script": state["script"],
        "director": state["director"],
        "visual_architect": visual_architect_payload,
        "coder": [],
        "failed_scenes": [],
        "max_parallel_coders": state["max_parallel_coders"],
        "last_action": "生成视觉规范",
    }


def dispatch_coders(state: State) -> List[Send]:
    director = state.get("director")
    visual_architect = state.get("visual_architect")

    if not director:
        scenes = []
    elif isinstance(director, dict):
        scenes = director.get("scenes", [])
    else:
        scenes = director.scenes

    if visual_architect is None:
        logger.error("Skipping coder dispatch because visual_architect is missing")
        return []

    planned_parallelism = max(1, state.get("max_parallel_coders", 4))
    logger.info(
        "Dispatching coder tasks scene_count=%s max_parallel_coders=%s visual_protocol_type=%s",
        len(scenes),
        planned_parallelism,
        type(visual_architect).__name__,
    )
    return [
        Send(
            "coder_node",
            CoderTaskState(scene=scene, visual_architect=visual_architect),
        )
        for scene in scenes
    ]


def coder_node(task: CoderTaskState, prompt_manager: PromptManager) -> dict:
    from agents.coder import coder_agent, example as coder_example

    try:
        if task.get("scene") is None:
            raise ValueError("Scene data is missing in coder_node.")
        if task.get("visual_architect") is None:
            raise ValueError(
                "Visual Architect design protocol is missing in coder_node. The architect agent might have failed."
            )

        scene_id = scene_id_of(task.get("scene"))
        logger.info("Coder node started scene_id=%s", scene_id)
        scene_json = to_json_payload(task["scene"])
        va_json = to_json_payload(task["visual_architect"])

        messages = prompt_manager.get_langchain_messages(
            coder_agent["prompt_name"], example=coder_example
        )
        messages.append(
            HumanMessage(
                f"【当前分镜】\n{scene_json}\n\n"
                f"【完整视觉设计协议】\n{va_json}"
            )
        )

        cache_key = build_cache_key(
            coder_agent["name"],
            scene_json,
            va_json,
        )
        result = coder_cache.get(cache_key, model_type=CoderResult)
        if result is None:
            result = invoke_structured(
                model=coder_agent["model"],
                schema=coder_agent["response_format"],
                messages=messages,
                operation=f"coder:{scene_id}",
            )
            coder_cache.set(cache_key, result)

        passed = qa_guard_check(result, prompt_manager)
        logger.info("Coder node finished scene_id=%s passed=%s", scene_id, passed)
        return {
            "coder": [result],
            "failed_scenes": [] if passed else [scene_id],
            "last_action": f"代码生成: 分镜 {scene_id}",
        }
    except Exception as exc:
        failed_scene_id = scene_id_of(task.get("scene"))
        logger.exception("Coder node failed scene_id=%s", failed_scene_id)
        return {
            "coder": [],
            "failed_scenes": [failed_scene_id],
            "last_action": f"代码生成致命错误: {str(exc)}",
        }


def build_workflow() -> StateGraph:
    prompt_manager = PromptManager()
    workflow = StateGraph(State)

    workflow.add_node("director_node", lambda state: director_node(state, prompt_manager))
    workflow.add_node(
        "visual_architect_node",
        lambda state: visual_architect_node(state, prompt_manager),
    )
    workflow.add_node("coder_node", lambda state: coder_node(state, prompt_manager))

    workflow.set_entry_point("director_node")
    workflow.add_edge("director_node", "visual_architect_node")
    workflow.add_conditional_edges("visual_architect_node", dispatch_coders, ["coder_node"])
    workflow.add_edge("coder_node", END)

    return workflow


def build_animation_workflow(checkpointer=None):
    workflow = build_workflow()
    if checkpointer is None:
        return workflow.compile()
    return workflow.compile(checkpointer=checkpointer)


def animation_work_flow(checkpointer=None):
    return build_animation_workflow(checkpointer=checkpointer)
