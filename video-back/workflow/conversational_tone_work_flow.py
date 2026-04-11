from typing import TypedDict

from langchain_core.messages import HumanMessage
from langgraph.constants import END
from langgraph.graph import StateGraph

from agents.content_reviewer import content_reviewer_agent
from agents.content_writer import content_writer_agent
from prompts.manager import PromptManager
from utils.cache import SimpleCache, build_cache_key

MAX_LOOPS = 3
MIN_SCORE_THRESHOLD = 80

writer_cache = SimpleCache()
reviewer_cache = SimpleCache()


class State(TypedDict):
    oral_content: str
    current_script: str
    review_score: int | None
    last_feedback: str | None
    loop_count: int


def content_writer(state: State, prompt_manager: PromptManager) -> State:
    writer_messages = prompt_manager.get_langchain_messages(content_writer_agent["prompt_name"])
    writer_messages.append(HumanMessage(f"原始口语内容：\n{state['oral_content']}"))

    if state["loop_count"] > 0 and state["last_feedback"]:
        writer_messages.append(HumanMessage(f"请根据以下反馈修改文案：\n{state['last_feedback']}"))
        writer_messages.append(HumanMessage(f"待修改文案：\n{state['current_script']}"))
    else:
        writer_messages.append(HumanMessage(f"请将以上内容口语化：\n{state['oral_content']}"))

    cache_key = build_cache_key(
        content_writer_agent["name"],
        state["oral_content"],
        state["current_script"],
        state["last_feedback"] or "",
        str(state["loop_count"]),
    )
    result = writer_cache.get(cache_key)
    if result is None:
        result = content_writer_agent["model"].invoke(writer_messages).content
        writer_cache.set(cache_key, result)

    return {
        "oral_content": state["oral_content"],
        "current_script": result,
        "review_score": state["review_score"],
        "last_feedback": state["last_feedback"],
        "loop_count": state["loop_count"],
    }


def content_reviewer(state: State, prompt_manager: PromptManager) -> State:
    reviewer_messages = prompt_manager.get_langchain_messages(content_reviewer_agent["prompt_name"])
    reviewer_messages.append(HumanMessage(f"请评估以下文案：\n{state['current_script']}"))

    cache_key = build_cache_key(content_reviewer_agent["name"], state["current_script"])
    result = reviewer_cache.get(cache_key)
    if result is None:
        result = content_reviewer_agent["model"].with_structured_output(
            content_reviewer_agent["response_format"]
        ).invoke(reviewer_messages)
        reviewer_cache.set(cache_key, result)

    return {
        "oral_content": state["oral_content"],
        "current_script": state["current_script"],
        "review_score": result.score,
        "last_feedback": result.feedback,
        "loop_count": state["loop_count"] + 1,
    }


def should_continue_evaluation(state: State) -> str:
    if state["review_score"] is None:
        return "continue_writing"
    if state["review_score"] < MIN_SCORE_THRESHOLD and state["loop_count"] < MAX_LOOPS:
        return "continue_writing"
    return "end"


def build_workflow() -> StateGraph:
    workflow = StateGraph(State)
    prompt_manager = PromptManager()

    workflow.add_node("content_writer", lambda state: content_writer(state, prompt_manager))
    workflow.add_node("content_reviewer", lambda state: content_reviewer(state, prompt_manager))
    workflow.set_entry_point("content_writer")
    workflow.add_edge("content_writer", "content_reviewer")
    workflow.add_conditional_edges(
        "content_reviewer",
        should_continue_evaluation,
        {
            "continue_writing": "content_writer",
            "end": END,
        },
    )
    return workflow


def build_conversational_tone_workflow(checkpointer=None):
    workflow = build_workflow()
    if checkpointer is None:
        return workflow.compile()
    return workflow.compile(checkpointer=checkpointer)


workflow = build_workflow()
app = workflow.compile()
