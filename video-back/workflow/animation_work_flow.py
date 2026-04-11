import operator
from typing import Annotated, List, TypedDict

from langchain_core.messages import HumanMessage
from langgraph.constants import END
from langgraph.graph import StateGraph
from langgraph.types import Send

from agents.coder import CoderResult
from agents.director import DirectorResult, Scene, director_agent, example as director_example
from agents.qa_guard import qa_guard_agent
from agents.visual_architect import (
    VisualProtocol,
    example as visual_architect_example,
    visual_architect_agent,
)
from prompts.manager import PromptManager
from utils.cache import SimpleCache, build_cache_key

coder_cache = SimpleCache()
director_cache = SimpleCache()
qa_cache = SimpleCache()
visual_architect_cache = SimpleCache()


class State(TypedDict):
    script: str
    director: DirectorResult | None
    visual_architect: VisualProtocol | None
    coder: Annotated[List[CoderResult], operator.add]
    failed_scenes: Annotated[List[str], operator.add]
    max_parallel_coders: int


class CoderTaskState(TypedDict):
    scene: Scene
    visual_architect: VisualProtocol


def qa_guard_check(result: CoderResult, prompt_manager: PromptManager) -> bool:
    messages = prompt_manager.get_langchain_messages(qa_guard_agent["prompt_name"])
    messages.append(
        HumanMessage(
            f"请检查以下代码是否可用。\n"
            f"scene_id: {result.scene_id}\n"
            f"code:\n{result.code}"
        )
    )

    cache_key = build_cache_key(qa_guard_agent["name"], result.scene_id, result.code)
    qa_result = qa_cache.get(cache_key)
    if qa_result is None:
        qa_result = qa_guard_agent["model"].with_structured_output(
            qa_guard_agent["response_format"]
        ).invoke(messages)
        qa_cache.set(cache_key, qa_result)

    return qa_result.status.strip().lower() != "fail"


def director_node(state: State, prompt_manager: PromptManager) -> State:
    messages = prompt_manager.get_langchain_messages(
        director_agent["prompt_name"], example=director_example
    )
    messages.append(HumanMessage(f"请根据以下脚本生成分镜脚本：\n{state['script']}"))

    cache_key = build_cache_key(director_agent["name"], state["script"])
    result = director_cache.get(cache_key)
    if result is None:
        result = director_agent["model"].with_structured_output(
            director_agent["response_format"]
        ).invoke(messages)
        director_cache.set(cache_key, result)

    return {
        "script": state["script"],
        "director": result,
        "visual_architect": state["visual_architect"],
        "coder": [],
        "failed_scenes": [],
        "max_parallel_coders": state["max_parallel_coders"],
    }


def visual_architect_node(state: State, prompt_manager: PromptManager) -> State:
    messages = prompt_manager.get_langchain_messages(
        visual_architect_agent["prompt_name"], example=visual_architect_example
    )
    messages.append(HumanMessage(f"请根据以下分镜脚本生成视觉设计：\n{state['director']}"))

    cache_key = build_cache_key(
        visual_architect_agent["name"], state["director"].model_dump_json()
    )
    result = visual_architect_cache.get(cache_key)
    if result is None:
        result = visual_architect_agent["model"].with_structured_output(
            visual_architect_agent["response_format"]
        ).invoke(messages)
        visual_architect_cache.set(cache_key, result)

    return {
        "script": state["script"],
        "director": state["director"],
        "visual_architect": result,
        "coder": [],
        "failed_scenes": [],
        "max_parallel_coders": state["max_parallel_coders"],
    }


def dispatch_coders(state: State) -> List[Send]:
    scenes = state["director"].scenes if state["director"] else []
    _ = max(1, state.get("max_parallel_coders", 4))
    return [
        Send(
            "coder_node",
            CoderTaskState(scene=scene, visual_architect=state["visual_architect"]),
        )
        for scene in scenes
    ]


def coder_node(task: CoderTaskState, prompt_manager: PromptManager) -> dict:
    from agents.coder import coder_agent, example as coder_example

    try:
        messages = prompt_manager.get_langchain_messages(
            coder_agent["prompt_name"], example=coder_example
        )
        messages.append(
            HumanMessage(
                f"【当前分镜】\n{task['scene'].model_dump_json(indent=2)}\n\n"
                f"【完整视觉设计协议】\n{task['visual_architect'].model_dump_json(indent=2)}"
            )
        )

        cache_key = build_cache_key(
            coder_agent["name"],
            task["scene"].model_dump_json(),
            task["visual_architect"].model_dump_json(),
        )
        result = coder_cache.get(cache_key)
        if result is None:
            result = coder_agent["model"].with_structured_output(
                coder_agent["response_format"]
            ).invoke(messages)
            coder_cache.set(cache_key, result)

        passed = qa_guard_check(result, prompt_manager)
        return {
            "coder": [result],
            "failed_scenes": [] if passed else [task["scene"].scene_id],
        }
    except Exception:
        return {"coder": [], "failed_scenes": [task["scene"].scene_id]}


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
