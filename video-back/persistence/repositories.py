from __future__ import annotations

import asyncio
from collections import defaultdict
from copy import deepcopy

from domain.artifacts.entities import ArtifactRecord, SceneArtifactRecord
from domain.sessions.entities import BranchRecord, SessionRecord, utcnow
from domain.tasks.entities import TaskRecord, TaskRunRecord
from domain.tasks.state_machine import TaskStateMachine
from orchestration.event_publisher import TaskEvent


class InMemorySessionRepository:
    def __init__(self) -> None:
        self._items: dict[str, SessionRecord] = {}
        self._lock = asyncio.Lock()

    async def create(self, session: SessionRecord) -> SessionRecord:
        async with self._lock:
            self._items[session.id] = session.model_copy(deep=True)
            return session

    async def get(self, session_id: str, user_id: str | None = None) -> SessionRecord | None:
        session = self._items.get(session_id)
        if session is None:
            return None
        if user_id is not None and session.user_id != user_id:
            return None
        return session.model_copy(deep=True)

    async def set_current_branch(self, session_id: str, branch_id: str) -> None:
        async with self._lock:
            session = self._items[session_id]
            session.current_branch_id = branch_id
            session.updated_at = utcnow()


class InMemoryBranchRepository:
    def __init__(self) -> None:
        self._items: dict[str, BranchRecord] = {}
        self._lock = asyncio.Lock()

    async def create(self, branch: BranchRecord) -> BranchRecord:
        async with self._lock:
            self._items[branch.id] = branch.model_copy(deep=True)
            return branch

    async def get(self, branch_id: str) -> BranchRecord | None:
        branch = self._items.get(branch_id)
        return None if branch is None else branch.model_copy(deep=True)

    async def list_by_session(self, session_id: str) -> list[BranchRecord]:
        return [
            branch.model_copy(deep=True)
            for branch in self._items.values()
            if branch.session_id == session_id
        ]

    async def update_head(self, branch_id: str, expected_version: int, head_artifact_id: str) -> bool:
        async with self._lock:
            branch = self._items.get(branch_id)
            if branch is None or branch.version != expected_version:
                return False
            branch.head_artifact_id = head_artifact_id
            branch.version += 1
            return True


class InMemoryTaskRepository:
    def __init__(self) -> None:
        self._items: dict[str, TaskRecord] = {}
        self._runs: dict[str, list[TaskRunRecord]] = defaultdict(list)
        self._lock = asyncio.Lock()

    async def create(self, task: TaskRecord) -> TaskRecord:
        async with self._lock:
            self._items[task.id] = task.model_copy(deep=True)
            return task

    async def get(self, task_id: str) -> TaskRecord | None:
        task = self._items.get(task_id)
        return None if task is None else task.model_copy(deep=True)

    async def list_by_session(self, session_id: str) -> list[TaskRecord]:
        tasks = [task for task in self._items.values() if task.session_id == session_id]
        tasks.sort(key=lambda item: item.created_at, reverse=True)
        return [task.model_copy(deep=True) for task in tasks]

    async def transition(self, task_id: str, from_status: str, to_status: str, **fields) -> bool:
        async with self._lock:
            task = self._items.get(task_id)
            if task is None or task.status != from_status:
                return False
            TaskStateMachine.ensure_transition(from_status, to_status)
            task.status = type(task.status)(to_status)
            for key, value in fields.items():
                setattr(task, key, value)
            return True

    async def update(self, task_id: str, **fields) -> TaskRecord:
        async with self._lock:
            task = self._items[task_id]
            for key, value in fields.items():
                setattr(task, key, value)
            return task.model_copy(deep=True)

    async def append_run(self, run: TaskRunRecord) -> TaskRunRecord:
        async with self._lock:
            self._runs[run.task_id].append(run.model_copy(deep=True))
            return run

    async def list_runs(self, task_id: str) -> list[TaskRunRecord]:
        return [run.model_copy(deep=True) for run in self._runs.get(task_id, [])]


class InMemoryEventRepository:
    def __init__(self) -> None:
        self._events: list[TaskEvent] = []
        self._task_subscribers: dict[str, list[asyncio.Queue[TaskEvent]]] = defaultdict(list)
        self._session_subscribers: dict[str, list[asyncio.Queue[TaskEvent]]] = defaultdict(list)
        self._lock = asyncio.Lock()

    async def append(self, event: TaskEvent) -> TaskEvent:
        async with self._lock:
            self._events.append(event)
            subscribers = [
                *self._task_subscribers.get(event.task_id, []),
                *self._session_subscribers.get(event.session_id, []),
            ]
        for queue in subscribers:
            await queue.put(event)
        return event

    async def list_by_task(self, task_id: str, after_id: str | None = None) -> list[TaskEvent]:
        items = [event for event in self._events if event.task_id == task_id]
        if after_id is None:
            return [deepcopy(event) for event in items]
        passed = False
        result: list[TaskEvent] = []
        for event in items:
            if passed:
                result.append(deepcopy(event))
            if event.id == after_id:
                passed = True
        return result

    async def list_timeline(self, session_id: str, branch_id: str | None = None, limit: int = 100) -> list[TaskEvent]:
        items = [event for event in self._events if event.session_id == session_id]
        if branch_id is not None:
            items = [event for event in items if event.branch_id == branch_id]
        items.sort(key=lambda event: event.created_at, reverse=True)
        return [deepcopy(event) for event in items[:limit]]

    async def subscribe_task(self, task_id: str) -> asyncio.Queue[TaskEvent]:
        queue: asyncio.Queue[TaskEvent] = asyncio.Queue()
        async with self._lock:
            self._task_subscribers[task_id].append(queue)
        return queue

    async def unsubscribe_task(self, task_id: str, queue: asyncio.Queue[TaskEvent]) -> None:
        async with self._lock:
            subscribers = self._task_subscribers.get(task_id, [])
            if queue in subscribers:
                subscribers.remove(queue)


class InMemoryArtifactRepository:
    def __init__(self) -> None:
        self._artifacts: dict[str, ArtifactRecord] = {}
        self._scene_artifacts: dict[str, SceneArtifactRecord] = {}
        self._artifact_versions: dict[tuple[str, str, str | None], int] = defaultdict(int)
        self._scene_versions: dict[tuple[str, str, str], int] = defaultdict(int)
        self._lock = asyncio.Lock()

    async def publish(self, artifact: ArtifactRecord) -> ArtifactRecord:
        async with self._lock:
            self._artifacts[artifact.id] = artifact.model_copy(deep=True)
            return artifact

    async def get(self, artifact_id: str) -> ArtifactRecord | None:
        artifact = self._artifacts.get(artifact_id)
        return None if artifact is None else artifact.model_copy(deep=True)

    async def latest(self, branch_id: str, artifact_type: str, artifact_subtype: str | None = None) -> ArtifactRecord | None:
        items = [
            artifact
            for artifact in self._artifacts.values()
            if artifact.branch_id == branch_id
            and artifact.artifact_type == artifact_type
            and artifact.artifact_subtype == artifact_subtype
        ]
        if not items:
            return None
        items.sort(key=lambda item: item.version, reverse=True)
        return items[0].model_copy(deep=True)

    async def next_version(self, branch_id: str, artifact_type: str, artifact_subtype: str | None = None) -> int:
        async with self._lock:
            key = (branch_id, artifact_type, artifact_subtype)
            self._artifact_versions[key] += 1
            return self._artifact_versions[key]

    async def list_by_branch(self, branch_id: str) -> list[ArtifactRecord]:
        items = [artifact for artifact in self._artifacts.values() if artifact.branch_id == branch_id]
        items.sort(key=lambda item: item.created_at, reverse=True)
        return [item.model_copy(deep=True) for item in items]

    async def publish_scene_artifact(self, scene_artifact: SceneArtifactRecord) -> SceneArtifactRecord:
        async with self._lock:
            self._scene_artifacts[scene_artifact.id] = scene_artifact.model_copy(deep=True)
            return scene_artifact

    async def get_scene_artifact(self, scene_artifact_id: str) -> SceneArtifactRecord | None:
        item = self._scene_artifacts.get(scene_artifact_id)
        return None if item is None else item.model_copy(deep=True)

    async def next_scene_version(self, session_id: str, branch_id: str, scene_id: str) -> int:
        async with self._lock:
            key = (session_id, branch_id, scene_id)
            self._scene_versions[key] += 1
            return self._scene_versions[key]

    async def list_scene_artifacts_by_artifact(self, artifact_id: str) -> list[SceneArtifactRecord]:
        items = [
            item for item in self._scene_artifacts.values() if item.artifact_id == artifact_id
        ]
        items.sort(key=lambda item: item.scene_order)
        return [item.model_copy(deep=True) for item in items]
