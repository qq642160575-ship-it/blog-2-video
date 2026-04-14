from __future__ import annotations

import time
from typing import Any

from app.errors import ArtifactNotFoundError, RenderFailedError
from domain.render_jobs.repository import RenderJobRepository
from orchestration.event_publisher import TaskEventPublisher
from persistence.repositories import InMemoryArtifactRepository
from rendering.preview_renderer import PreviewRenderer
from rendering.schemas import RenderResult
from rendering.visual_validator import VisualValidator
from utils.logger import get_logger

logger = get_logger(__name__)


class RenderPreviewPipeline:
    """
    渲染预览管道

    职责:
    1. 接收 scene_artifact_id 或 scene_code
    2. 使用 PreviewRenderer 渲染场景
    3. 使用 VisualValidator 验证渲染结果
    4. 保存 preview_image_url 到 scene_artifact
    5. 创建 render_job 记录
    6. 发布验证事件
    """

    def __init__(
        self,
        renderer: PreviewRenderer,
        validator: VisualValidator,
        artifact_repo: InMemoryArtifactRepository,
        render_job_repo: RenderJobRepository,
        event_publisher: TaskEventPublisher,
    ) -> None:
        self.renderer = renderer
        self.validator = validator
        self.artifact_repo = artifact_repo
        self.render_job_repo = render_job_repo
        self.event_publisher = event_publisher

    async def render_scene(
        self,
        scene_artifact_id: str,
        task_id: str,
        session_id: str,
        branch_id: str,
        task_run_id: str | None = None,
        frame: int = 0,
        validate: bool = True,
    ) -> dict[str, Any]:
        """
        渲染场景预览

        Args:
            scene_artifact_id: 场景 artifact ID
            frame: 渲染帧数 (默认 0)
            validate: 是否验证渲染结果

        Returns:
            dict 包含:
                - render_result: RenderResult
                - validation_report: VisualValidationReport (如果 validate=True)
                - render_job_id: str

        Raises:
            ArtifactNotFoundError: 场景 artifact 不存在
            RenderFailedError: 渲染失败
        """
        start_time = time.time()

        # 1. 获取场景 artifact
        scene_artifact = await self.artifact_repo.get_artifact(scene_artifact_id)
        if not scene_artifact:
            raise ArtifactNotFoundError(f"Scene artifact not found: {scene_artifact_id}")

        scene_id = scene_artifact.artifact_id
        scene_code = scene_artifact.content.get("code", "")

        if not scene_code:
            raise RenderFailedError(f"Scene code is empty for {scene_id}")

        logger.info(f"Rendering scene {scene_id} at frame {frame}")

        # 创建 render_job 记录
        render_job_id = f"rj_{scene_id}_{int(time.time() * 1000)}"
        await self.render_job_repo.create_render_job(
            job_id=render_job_id,
            scene_artifact_id=scene_artifact_id,
            scene_id=scene_id,
            frame=frame,
        )

        # 发布渲染开始事件
        await self.event_publisher.publish(
            event_type="render.started",
            task_id=task_id,
            session_id=session_id,
            branch_id=branch_id,
            task_run_id=task_run_id,
            scene_id=scene_id,
            payload={
                "scene_artifact_id": scene_artifact_id,
                "render_job_id": render_job_id,
                "frame": frame,
            },
        )

        try:
            # 更新状态为 rendering
            await self.render_job_repo.update_render_job_status(
                job_id=render_job_id,
                status="rendering",
            )
            # 2. 渲染场景
            render_result: RenderResult = await self.renderer.render_scene_preview(
                scene_code=scene_code,
                scene_id=scene_id,
                frame=frame,
            )

            logger.info(
                f"Rendered scene {scene_id} in {render_result.render_time_ms:.2f}ms, "
                f"saved to {render_result.storage_url}"
            )

            # 3. 验证渲染结果
            validation_report = None
            if validate:
                # 更新状态为 validating
                await self.render_job_repo.update_render_job_status(
                    job_id=render_job_id,
                    status="validating",
                    storage_url=render_result.storage_url,
                    render_time_ms=render_result.render_time_ms,
                )

                validation_report = await self.validator.validate(
                    scene_id=scene_id,
                    preview_image_url=render_result.storage_url,
                    expected_width=render_result.width,
                    expected_height=render_result.height,
                )

                logger.info(
                    f"Validation for {scene_id}: "
                    f"passed={validation_report.passed}, "
                    f"issues={len(validation_report.issues)}"
                )

                # 发布验证事件
                await self.event_publisher.publish(
                    event_type="render.validated",
                    task_id=task_id,
                    session_id=session_id,
                    branch_id=branch_id,
                    task_run_id=task_run_id,
                    scene_id=scene_id,
                    payload={
                        "render_job_id": render_job_id,
                        "passed": validation_report.passed,
                        "issues": [issue.model_dump() for issue in validation_report.issues],
                    },
                )

            # 4. 更新 scene_artifact 的 preview_image_url
            updated_content = scene_artifact.content.copy()
            updated_content["preview_image_url"] = render_result.storage_url
            updated_content["preview_metadata"] = {
                "width": render_result.width,
                "height": render_result.height,
                "frame": render_result.frame,
                "render_time_ms": render_result.render_time_ms,
                "renderer": render_result.metadata.get("renderer", "unknown"),
            }

            await self.artifact_repo.update_artifact_content(
                artifact_id=scene_artifact_id,
                content=updated_content,
            )

            # 5. 更新 render_job 为 completed
            await self.render_job_repo.update_render_job_status(
                job_id=render_job_id,
                status="completed",
                storage_url=render_result.storage_url,
                render_time_ms=render_result.render_time_ms,
                validation_passed=validation_report.passed if validation_report else None,
                validation_issues=[issue.model_dump() for issue in validation_report.issues]
                if validation_report
                else None,
            )

            # 发布渲染完成事件
            total_time_ms = (time.time() - start_time) * 1000
            await self.event_publisher.publish(
                event_type="render.completed",
                task_id=task_id,
                session_id=session_id,
                branch_id=branch_id,
                task_run_id=task_run_id,
                scene_id=scene_id,
                payload={
                    "render_job_id": render_job_id,
                    "storage_url": render_result.storage_url,
                    "total_time_ms": total_time_ms,
                    "validation_passed": validation_report.passed if validation_report else None,
                },
            )

            return {
                "render_result": render_result.model_dump(),
                "validation_report": validation_report.model_dump() if validation_report else None,
                "render_job_id": render_job_id,
            }

        except Exception as e:
            logger.error(f"Render failed for {scene_id}: {e}")

            # 更新 render_job 为 failed
            await self.render_job_repo.update_render_job_status(
                job_id=render_job_id,
                status="failed",
                error_message=str(e),
            )

            # 发布渲染失败事件
            await self.event_publisher.publish(
                event_type="render.failed",
                task_id=task_id,
                session_id=session_id,
                branch_id=branch_id,
                task_run_id=task_run_id,
                scene_id=scene_id,
                payload={
                    "scene_artifact_id": scene_artifact_id,
                    "render_job_id": render_job_id,
                    "error": str(e),
                },
            )

            raise RenderFailedError(f"Render failed for {scene_id}: {e}") from e

    async def render_all_scenes(
        self,
        scene_artifact_ids: list[str],
        task_id: str,
        session_id: str,
        branch_id: str,
        task_run_id: str | None = None,
        frame: int = 0,
        validate: bool = True,
    ) -> dict[str, Any]:
        """
        批量渲染多个场景

        Args:
            scene_artifact_ids: 场景 artifact ID 列表
            frame: 渲染帧数
            validate: 是否验证渲染结果

        Returns:
            dict 包含:
                - results: list[dict] - 每个场景的渲染结果
                - summary: dict - 汇总信息
        """
        results = []
        failed_count = 0
        validation_failed_count = 0

        for scene_artifact_id in scene_artifact_ids:
            try:
                result = await self.render_scene(
                    scene_artifact_id=scene_artifact_id,
                    task_id=task_id,
                    session_id=session_id,
                    branch_id=branch_id,
                    task_run_id=task_run_id,
                    frame=frame,
                    validate=validate,
                )
                results.append(
                    {
                        "scene_artifact_id": scene_artifact_id,
                        "success": True,
                        "result": result,
                    }
                )

                # 统计验证失败
                if validate and result.get("validation_report"):
                    if not result["validation_report"]["passed"]:
                        validation_failed_count += 1

            except Exception as e:
                logger.error(f"Failed to render {scene_artifact_id}: {e}")
                results.append(
                    {
                        "scene_artifact_id": scene_artifact_id,
                        "success": False,
                        "error": str(e),
                    }
                )
                failed_count += 1

        return {
            "results": results,
            "summary": {
                "total": len(scene_artifact_ids),
                "succeeded": len(scene_artifact_ids) - failed_count,
                "failed": failed_count,
                "validation_failed": validation_failed_count,
            },
        }
