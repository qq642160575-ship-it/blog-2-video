from __future__ import annotations

from domain.artifacts.service import ArtifactService
from domain.common.enums import ArtifactType, SessionStatus
from domain.sessions.entities import BranchRecord, SessionRecord
from persistence.repositories import BranchRepository, SessionRepository


class SessionService:
    def __init__(
        self,
        session_repo: SessionRepository,
        branch_repo: BranchRepository,
        artifact_service: ArtifactService,
    ) -> None:
        self.session_repo = session_repo
        self.branch_repo = branch_repo
        self.artifact_service = artifact_service

    async def create_session(
        self,
        source_type: str,
        source_content: str,
        title: str | None = None,
        user_id: str | None = None,
        user_preference: dict | None = None,
    ) -> tuple[SessionRecord, BranchRecord, str]:
        session = SessionRecord(
            user_id=user_id,
            title=title,
            source_type=source_type,
            source_content=source_content,
            status=SessionStatus.ACTIVE,
            user_preference=user_preference or {},
        )
        await self.session_repo.create(session)

        branch = BranchRecord(session_id=session.id, name="main")
        await self.branch_repo.create(branch)

        await self.session_repo.set_current_branch(session.id, branch.id)

        source_artifact = await self.artifact_service.publish_artifact(
            session_id=session.id,
            branch_id=branch.id,
            task_id=None,
            artifact_type=ArtifactType.SOURCE_DOCUMENT,
            content_text=source_content,
            content_json={
                "source_type": source_type,
                "title": title,
                "user_preference": user_preference or {},
            },
            summary="源文档",
            publish_event=False,
        )

        return session, branch, source_artifact.id

    async def get_session(self, session_id: str, user_id: str | None = None) -> SessionRecord | None:
        return await self.session_repo.get(session_id, user_id=user_id)

    async def list_sessions(
        self,
        user_id: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[SessionRecord]:
        return await self.session_repo.list_by_user(user_id=user_id, limit=limit, offset=offset)

    async def archive_session(self, session_id: str) -> bool:
        session = await self.session_repo.get(session_id)
        if session is None:
            return False
        return await self.session_repo.update_status(session_id, SessionStatus.ARCHIVED)

    async def get_current_branch(self, session_id: str) -> BranchRecord | None:
        session = await self.session_repo.get(session_id)
        if session is None or session.current_branch_id is None:
            return None
        return await self.branch_repo.get(session.current_branch_id)

    async def switch_branch(self, session_id: str, branch_id: str) -> bool:
        branch = await self.branch_repo.get(branch_id)
        if branch is None or branch.session_id != session_id:
            return False
        await self.session_repo.set_current_branch(session_id, branch_id)
        return True
