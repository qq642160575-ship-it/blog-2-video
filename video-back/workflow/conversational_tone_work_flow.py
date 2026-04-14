from __future__ import annotations

from typing import TypedDict

from langchain_core.messages import HumanMessage
from langgraph.constants import END
from langgraph.graph import StateGraph

from agents.content_reviewer import Result as ReviewerResult
from agents.content_reviewer import content_reviewer_agent
from agents.content_writer import Result as WriterResult
from agents.content_writer import content_writer_agent
from compiler.parser import parse_script
from compiler.schemas import OralScriptResult
from models.get_model import FallbackModel
from prompts.manager import PromptManager
from utils.cache import SimpleCache, build_cache_key
from utils.logger import get_logger
from utils.structured_output import invoke_structured

MAX_LOOPS = 3
MIN_SCORE_THRESHOLD = 80

writer_cache = SimpleCache()
reviewer_cache = SimpleCache()
logger = get_logger(__name__)


class State(TypedDict):
    source_text: str
    current_script: str
    review_score: int | None
    last_feedback: str | None
    loop_count: int
    oral_script_result: dict | None
    last_action: str | None


def _fallback_oral_script(source_text: str) -> str:
    text = " ".join(source_text.split())
    if not text:
        return ""
    if text.endswith(("。", "！", "？", "!", "?")):
        return text
    return f"{text}。"


def rewrite_oral_script_node(state: State, prompt_manager: PromptManager) -> State:
    logger.info("Oral rewrite started loop_count=%s", state["loop_count"])
    messages = prompt_manager.get_langchain_messages(content_writer_agent["prompt_name"])
    messages.append(HumanMessage(f"原始文章内容：\n{state['source_text']}"))
    if state["loop_count"] > 0 and state["last_feedback"]:
        messages.append(HumanMessage(f"请根据反馈继续优化为短视频口语稿：\n{state['last_feedback']}"))
        messages.append(HumanMessage(f"当前口语稿：\n{state['current_script']}"))
    else:
        messages.append(HumanMessage("请将以上文章改写为适合短视频讲述的口语化文案。"))

    cache_key = build_cache_key(
        "oral-script-rewrite",
        state["source_text"],
        state["current_script"],
        state["last_feedback"] or "",
        str(state["loop_count"]),
    )
    result = writer_cache.get(cache_key, model_type=WriterResult)
    if result is None:
        model = content_writer_agent["model"]
        try:
            if isinstance(model, FallbackModel):
                raise RuntimeError(model.reason)
            result = invoke_structured(
                model=model,
                schema=content_writer_agent["response_format"],
                messages=messages,
                operation=f"oral_script_rewrite:loop_{state['loop_count']}",
            )
        except Exception as exc:
            logger.warning("Oral rewrite model unavailable, using deterministic fallback: %s", exc)
            result = WriterResult(oral_script=_fallback_oral_script(state["current_script"] or state["source_text"]))
        writer_cache.set(cache_key, result)

    return {
        "source_text": state["source_text"],
        "current_script": result.oral_script.strip(),
        "review_score": state["review_score"],
        "last_feedback": state["last_feedback"],
        "loop_count": state["loop_count"],
        "oral_script_result": state["oral_script_result"],
        "last_action": "生成或修改口语稿",
    }


def review_oral_script_node(state: State, prompt_manager: PromptManager) -> State:
    logger.info("Oral review started loop_count=%s", state["loop_count"])
    messages = prompt_manager.get_langchain_messages(content_reviewer_agent["prompt_name"])
    messages.append(HumanMessage(f"请评估以下口语稿：\n{state['current_script']}"))

    cache_key = build_cache_key("oral-script-review", state["current_script"])
    result = reviewer_cache.get(cache_key, model_type=ReviewerResult)
    if result is None:
        model = content_reviewer_agent["model"]
        try:
            if isinstance(model, FallbackModel):
                raise RuntimeError(model.reason)
            result = invoke_structured(
                model=model,
                schema=content_reviewer_agent["response_format"],
                messages=messages,
                operation=f"oral_script_review:loop_{state['loop_count']}",
            )
        except Exception as exc:
            logger.warning("Oral review model unavailable, using deterministic fallback: %s", exc)
            result = ReviewerResult(score=85, feedback="模型不可用，已使用规则降级口语稿，可继续进入动画编译。")
        reviewer_cache.set(cache_key, result)

    return {
        "source_text": state["source_text"],
        "current_script": state["current_script"],
        "review_score": result.score,
        "last_feedback": result.feedback,
        "loop_count": state["loop_count"] + 1,
        "oral_script_result": state["oral_script_result"],
        "last_action": f"口语稿评审 (得分: {result.score})",
    }


def finalize_oral_script_node(state: State) -> State:
    logger.info("Finalizing oral script result")
    parsed = parse_script(state["current_script"])
    result = OralScriptResult(
        source_text=state["source_text"],
        oral_script=state["current_script"],
        script_segments=parsed.segments,
        script_metadata={
            "tone": "conversational",
            "target_duration_sec": max(15, min(90, len(state["current_script"]) // 6)),
        },
        review_score=state["review_score"],
        feedback=state["last_feedback"],
    )
    return {
        "source_text": state["source_text"],
        "current_script": state["current_script"],
        "review_score": state["review_score"],
        "last_feedback": state["last_feedback"],
        "loop_count": state["loop_count"],
        "oral_script_result": result.model_dump(),
        "last_action": "口语稿定稿完成",
    }


def should_continue_review(state: State) -> str:
    if state["review_score"] is None:
        return "continue"
    if state["review_score"] < MIN_SCORE_THRESHOLD and state["loop_count"] < MAX_LOOPS:
        return "continue"
    return "finalize"


def build_workflow() -> StateGraph:
    prompt_manager = PromptManager()
    workflow = StateGraph(State)
    workflow.add_node("rewrite_oral_script_node", lambda state: rewrite_oral_script_node(state, prompt_manager))
    workflow.add_node("review_oral_script_node", lambda state: review_oral_script_node(state, prompt_manager))
    workflow.add_node("finalize_oral_script_node", finalize_oral_script_node)
    workflow.set_entry_point("rewrite_oral_script_node")
    workflow.add_edge("rewrite_oral_script_node", "review_oral_script_node")
    workflow.add_conditional_edges(
        "review_oral_script_node",
        should_continue_review,
        {
            "continue": "rewrite_oral_script_node",
            "finalize": "finalize_oral_script_node",
        },
    )
    workflow.add_edge("finalize_oral_script_node", END)
    return workflow


def build_conversational_tone_workflow(checkpointer=None):
    workflow = build_workflow()
    if checkpointer is None:
        return workflow.compile()
    return workflow.compile(checkpointer=checkpointer)
