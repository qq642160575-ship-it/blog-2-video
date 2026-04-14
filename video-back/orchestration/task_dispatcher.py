from __future__ import annotations

from domain.common.enums import TaskType
from pipelines.base import Pipeline


class TaskDispatcher:
    def __init__(self, pipelines: dict[TaskType, Pipeline]) -> None:
        self._pipelines = pipelines

    def resolve(self, task_type: TaskType) -> Pipeline:
        try:
            return self._pipelines[task_type]
        except KeyError as exc:
            raise ValueError(f"Unsupported task type: {task_type}") from exc
