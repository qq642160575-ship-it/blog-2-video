from __future__ import annotations

from datetime import datetime, timezone

from domain.common.enums import TaskStatus
from domain.tasks.entities import TaskRunRecord
from orchestration.event_publisher import InMemoryEventPublisher
from orchestration.task_context import CancellationToken, TaskCancelledError, TaskContext
from orchestration.task_dispatcher import TaskDispatcher
from persistence.repositories import InMemoryTaskRepository


class TaskRunner:
    def __init__(
        self,
        task_repo: InMemoryTaskRepository,
        dispatcher: TaskDispatcher,
        event_publisher: InMemoryEventPublisher,
    ) -> None:
        self.task_repo = task_repo
        self.dispatcher = dispatcher
        self.event_publisher = event_publisher

    async def run(self, task_id: str) -> None:
        task = await self.task_repo.get(task_id)
        if task is None:
            return
        transitioned = await self.task_repo.transition(
            task.id,
            TaskStatus.QUEUED.value,
            TaskStatus.RUNNING.value,
            started_at=task.started_at or datetime.now(timezone.utc),
        )
        if not transitioned:
            return
        task = await self.task_repo.get(task_id)
        if task is None:
            return

        run = TaskRunRecord(task_id=task.id)
        await self.task_repo.append_run(run)
        await self.event_publisher.publish(
            "task.started",
            task_id=task.id,
            task_run_id=run.id,
            session_id=task.session_id,
            branch_id=task.branch_id,
        )

        async def is_cancelled() -> bool:
            current = await self.task_repo.get(task.id)
            return current is None or current.cancellation_requested

        context = TaskContext(
            task=task,
            run=run,
            request_payload=task.request_payload,
            baseline_artifact_id=task.baseline_artifact_id,
            cancellation_token=CancellationToken(is_cancelled),
        )

        try:
            pipeline = self.dispatcher.resolve(task.task_type)
            result = await pipeline.run(context)
            if await is_cancelled():
                raise TaskCancelledError("Task cancelled before completion")
            await self.task_repo.transition(
                task.id,
                TaskStatus.RUNNING.value,
                TaskStatus.SUCCEEDED.value,
                result_summary=result.summary,
                finished_at=datetime.now(timezone.utc),
            )
            await self.event_publisher.publish(
                "task.completed",
                task_id=task.id,
                task_run_id=run.id,
                session_id=task.session_id,
                branch_id=task.branch_id,
                payload=result.model_dump(),
            )
        except TaskCancelledError:
            await self.task_repo.transition(
                task.id,
                TaskStatus.RUNNING.value,
                TaskStatus.CANCELLED.value,
                finished_at=datetime.now(timezone.utc),
            )
            await self.event_publisher.publish(
                "task.cancelled",
                task_id=task.id,
                task_run_id=run.id,
                session_id=task.session_id,
                branch_id=task.branch_id,
            )
        except Exception as exc:
            await self.task_repo.transition(
                task.id,
                TaskStatus.RUNNING.value,
                TaskStatus.FAILED.value,
                error_message=str(exc),
                finished_at=datetime.now(timezone.utc),
            )
            await self.event_publisher.publish(
                "task.failed",
                task_id=task.id,
                task_run_id=run.id,
                session_id=task.session_id,
                branch_id=task.branch_id,
                event_level="error",
                payload={"message": str(exc)},
            )
