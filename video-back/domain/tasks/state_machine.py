from __future__ import annotations


class TaskStateTransitionError(ValueError):
    pass


class TaskStateMachine:
    ALLOWED_TRANSITIONS: dict[str, set[str]] = {
        "pending": {"queued", "cancelled"},
        "queued": {"running", "cancelled"},
        "running": {"succeeded", "failed", "cancelled", "blocked"},
        "failed": {"retrying"},
        "retrying": {"queued", "cancelled"},
        "blocked": {"queued", "cancelled"},
        "succeeded": set(),
        "cancelled": set(),
    }

    @classmethod
    def can_transition(cls, from_status: str, to_status: str) -> bool:
        return to_status in cls.ALLOWED_TRANSITIONS.get(from_status, set())

    @classmethod
    def ensure_transition(cls, from_status: str, to_status: str) -> None:
        if cls.can_transition(from_status, to_status):
            return
        raise TaskStateTransitionError(
            f"Invalid task state transition: {from_status} -> {to_status}"
        )
