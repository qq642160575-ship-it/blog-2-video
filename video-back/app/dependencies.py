from __future__ import annotations

import asyncio

from domain.artifacts.service import ArtifactService
from domain.common.enums import TaskType
from infra.queue.inline_queue import InlineTaskQueue
from orchestration.event_publisher import InMemoryEventPublisher
from orchestration.task_dispatcher import TaskDispatcher
from orchestration.task_runner import TaskRunner
from persistence.repositories import (
    InMemoryArtifactRepository,
    InMemoryBranchRepository,
    InMemoryEventRepository,
    InMemorySessionRepository,
    InMemoryTaskRepository,
)
from workers.task_worker import TaskWorker


class AppContainer:
    def __init__(self, use_real_workflow: bool = True) -> None:
        self.session_repo = InMemorySessionRepository()
        self.branch_repo = InMemoryBranchRepository()
        self.task_repo = InMemoryTaskRepository()
        self.event_repo = InMemoryEventRepository()
        self.artifact_repo = InMemoryArtifactRepository()
        self.event_publisher = InMemoryEventPublisher(self.event_repo)
        self.artifact_service = ArtifactService(
            artifact_repo=self.artifact_repo,
            branch_repo=self.branch_repo,
            event_publisher=self.event_publisher,
        )
        self.workflow_runner = None
        pipelines = {}
        if use_real_workflow:
            from orchestration.workflow_runner import WorkflowRunner
            from pipelines.create_video import CreateVideoPipeline

            self.workflow_runner = WorkflowRunner(
                artifact_service=self.artifact_service,
                artifact_repo=self.artifact_repo,
                event_publisher=self.event_publisher,
            )
            pipelines[TaskType.CREATE_VIDEO] = CreateVideoPipeline(
                workflow_runner=self.workflow_runner,
                artifact_repo=self.artifact_repo,
            )
        self.dispatcher = TaskDispatcher(pipelines)
        self.queue = InlineTaskQueue()
        self.task_runner = TaskRunner(
            task_repo=self.task_repo,
            dispatcher=self.dispatcher,
            event_publisher=self.event_publisher,
        )
        self.worker = TaskWorker(self.queue, self.task_runner)
        self.worker_task: asyncio.Task[None] | None = None

    async def start(self) -> None:
        if self.worker_task is None or self.worker_task.done():
            self.worker_task = asyncio.create_task(self.worker.run_forever())

    async def stop(self) -> None:
        await self.worker.stop()
        if self.worker_task is not None:
            self.worker_task.cancel()


def get_container() -> AppContainer:
    global _container
    if _container is None:
        _container = AppContainer()
    return _container


_container: AppContainer | None = None
