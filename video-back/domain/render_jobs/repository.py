from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from domain.render_jobs.entities import RenderJobRecord
from persistence.models import RenderJobModel
from utils.logger import get_logger

logger = get_logger(__name__)


class RenderJobRepository:
    """渲染任务仓储"""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create_render_job(
        self,
        job_id: str,
        scene_artifact_id: str,
        scene_id: str,
        frame: int = 0,
        metadata: dict[str, Any] | None = None,
    ) -> RenderJobRecord:
        """创建渲染任务"""
        model = RenderJobModel(
            job_id=job_id,
            scene_artifact_id=scene_artifact_id,
            scene_id=scene_id,
            status="pending",
            frame=frame,
            metadata=metadata or {},
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        self.session.add(model)
        await self.session.commit()
        await self.session.refresh(model)

        logger.info(f"Created render job {job_id} for scene {scene_id}")

        return self._to_record(model)

    async def get_render_job(self, job_id: str) -> RenderJobRecord | None:
        """获取渲染任务"""
        stmt = select(RenderJobModel).where(RenderJobModel.job_id == job_id)
        result = await self.session.execute(stmt)
        model = result.scalar_one_or_none()

        if not model:
            return None

        return self._to_record(model)

    async def update_render_job_status(
        self,
        job_id: str,
        status: str,
        storage_url: str | None = None,
        render_time_ms: float | None = None,
        validation_passed: bool | None = None,
        validation_issues: list[dict[str, Any]] | None = None,
        error_message: str | None = None,
    ) -> RenderJobRecord | None:
        """更新渲染任务状态"""
        stmt = select(RenderJobModel).where(RenderJobModel.job_id == job_id)
        result = await self.session.execute(stmt)
        model = result.scalar_one_or_none()

        if not model:
            return None

        model.status = status
        model.updated_at = datetime.utcnow()

        if storage_url is not None:
            model.storage_url = storage_url
        if render_time_ms is not None:
            model.render_time_ms = render_time_ms
        if validation_passed is not None:
            model.validation_passed = validation_passed
        if validation_issues is not None:
            model.validation_issues = validation_issues
        if error_message is not None:
            model.error_message = error_message

        await self.session.commit()
        await self.session.refresh(model)

        logger.info(f"Updated render job {job_id} status to {status}")

        return self._to_record(model)

    async def list_render_jobs_by_scene(
        self,
        scene_artifact_id: str,
        limit: int = 10,
    ) -> list[RenderJobRecord]:
        """列出场景的渲染任务"""
        stmt = (
            select(RenderJobModel)
            .where(RenderJobModel.scene_artifact_id == scene_artifact_id)
            .order_by(RenderJobModel.created_at.desc())
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        models = result.scalars().all()

        return [self._to_record(model) for model in models]

    def _to_record(self, model: RenderJobModel) -> RenderJobRecord:
        """转换为记录对象"""
        return RenderJobRecord(
            job_id=model.job_id,
            scene_artifact_id=model.scene_artifact_id,
            scene_id=model.scene_id,
            status=model.status,
            frame=model.frame,
            storage_url=model.storage_url,
            render_time_ms=model.render_time_ms,
            validation_passed=model.validation_passed,
            validation_issues=model.validation_issues or [],
            error_message=model.error_message,
            metadata=model.metadata or {},
            created_at=model.created_at,
            updated_at=model.updated_at,
        )
