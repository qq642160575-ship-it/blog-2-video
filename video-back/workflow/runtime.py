from langgraph.checkpoint.memory import InMemorySaver

from workflow.animation_work_flow import build_animation_workflow
from workflow.conversational_tone_work_flow import build_conversational_tone_workflow

WORKFLOW_NAMES = ("conversational_tone", "animation")

_CHECKPOINTERS = {
    "conversational_tone": InMemorySaver(),
    "animation": InMemorySaver(),
}

_WORKFLOWS = {
    "conversational_tone": build_conversational_tone_workflow(
        checkpointer=_CHECKPOINTERS["conversational_tone"]
    ),
    "animation": build_animation_workflow(checkpointer=_CHECKPOINTERS["animation"]),
}


def get_workflow(workflow_name: str):
    workflow = _WORKFLOWS.get(workflow_name)
    if workflow is None:
        raise KeyError(f"Unknown workflow: {workflow_name}")
    return workflow
