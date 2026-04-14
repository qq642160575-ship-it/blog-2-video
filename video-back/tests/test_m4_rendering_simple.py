import pytest
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker


@pytest.fixture
async def db_session():
    """创建测试数据库会话"""
    from persistence.models import Base

    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)

    # 创建表
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async_session_maker = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session_maker() as session:
        yield session


@pytest.fixture
def artifact_repo():
    from persistence.repositories import InMemoryArtifactRepository
    return InMemoryArtifactRepository()


@pytest.fixture
def event_publisher():
    from orchestration.event_publisher import InMemoryEventPublisher
    return InMemoryEventPublisher()


@pytest.mark.asyncio
async def test_render_preview_pipeline_basic(artifact_repo, event_publisher, db_session):
    """测试 RenderPreviewPipeline 基本功能"""
    # 延迟导入以避免循环依赖
    from domain.render_jobs.repository import RenderJobRepository
    from pipelines.render_preview_pipeline import RenderPreviewPipeline
    from rendering.preview_renderer import MockPreviewRenderer
    from rendering.visual_validator import VisualValidator
    from domain.artifacts.entities import ArtifactRecord

    render_job_repo = RenderJobRepository(db_session)
    renderer = MockPreviewRenderer()
    validator = VisualValidator()

    pipeline = RenderPreviewPipeline(
        renderer=renderer,
        validator=validator,
        artifact_repo=artifact_repo,
        render_job_repo=render_job_repo,
        event_publisher=event_publisher,
    )

    # 创建测试 artifact
    scene_artifact = ArtifactRecord(
        id="test_scene_1",
        artifact_id="test_scene_1",
        session_id="test_session",
        branch_id="test_branch",
        task_id="test_task",
        artifact_type="scene",
        content={
            "scene_id": "scene_1",
            "code": "export const Scene1 = () => <div>Test</div>;",
        },
        summary="测试场景",
        created_at=datetime.utcnow(),
    )
    await artifact_repo.save_artifact(scene_artifact)

    # 渲染场景
    result = await pipeline.render_scene(
        scene_artifact_id="test_scene_1",
        task_id="test_task",
        session_id="test_session",
        branch_id="test_branch",
        task_run_id="test_run",
        frame=0,
        validate=True,
    )

    # 验证结果
    assert "render_result" in result
    assert "validation_report" in result
    assert "render_job_id" in result

    render_result = result["render_result"]
    assert render_result["scene_id"] == "scene_1"
    assert render_result["storage_url"] is not None
    assert render_result["width"] == 1080
    assert render_result["height"] == 1920

    validation_report = result["validation_report"]
    assert validation_report is not None
    assert "passed" in validation_report
    assert "issues" in validation_report

    # 验证 artifact 已更新
    updated_artifact = await artifact_repo.get_artifact("test_scene_1")
    assert updated_artifact is not None
    assert "preview_image_url" in updated_artifact.content
    assert updated_artifact.content["preview_image_url"] == render_result["storage_url"]
    assert "preview_metadata" in updated_artifact.content

    # 验证 render_job 已创建
    render_job = await render_job_repo.get_render_job(result["render_job_id"])
    assert render_job is not None
    assert render_job.scene_id == "scene_1"
    assert render_job.status == "completed"
    assert render_job.storage_url == render_result["storage_url"]


@pytest.mark.asyncio
async def test_mock_renderer_creates_preview_file(artifact_repo, event_publisher, db_session):
    """测试 MockPreviewRenderer 创建预览文件"""
    from rendering.preview_renderer import MockPreviewRenderer

    renderer = MockPreviewRenderer()

    result = await renderer.render_scene_preview(
        scene_code="export const Scene = () => <div>Test</div>;",
        scene_id="test_scene",
        frame=0,
    )

    assert result.scene_id == "test_scene"
    assert result.storage_url is not None
    assert result.width == 1080
    assert result.height == 1920
    assert result.frame == 0
    assert result.render_time_ms > 0
    assert result.metadata["renderer"] == "mock"

    # 验证文件存在
    from pathlib import Path
    preview_path = Path(result.storage_url)
    assert preview_path.exists()


@pytest.mark.asyncio
async def test_visual_validator_checks_file_existence(artifact_repo, event_publisher, db_session):
    """测试 VisualValidator 检查文件存在性"""
    from rendering.visual_validator import VisualValidator

    validator = VisualValidator()

    # 测试不存在的文件
    report = await validator.validate(
        scene_id="test_scene",
        preview_image_url="/nonexistent/file.png",
        expected_width=1080,
        expected_height=1920,
    )

    assert report.scene_id == "test_scene"
    assert report.passed is False
    assert len(report.issues) > 0
    assert report.issues[0].code == "IMAGE_NOT_FOUND"
    assert report.issues[0].severity == "error"


@pytest.mark.asyncio
async def test_render_job_repository_crud(db_session):
    """测试 RenderJobRepository CRUD 操作"""
    from domain.render_jobs.repository import RenderJobRepository

    repo = RenderJobRepository(db_session)

    # 创建 render_job
    job = await repo.create_render_job(
        job_id="test_job_1",
        scene_artifact_id="scene_artifact_1",
        scene_id="scene_1",
        frame=0,
    )

    assert job.job_id == "test_job_1"
    assert job.scene_id == "scene_1"
    assert job.status == "pending"

    # 更新状态
    updated_job = await repo.update_render_job_status(
        job_id="test_job_1",
        status="completed",
        storage_url="/path/to/preview.png",
        render_time_ms=123.45,
        validation_passed=True,
    )

    assert updated_job is not None
    assert updated_job.status == "completed"
    assert updated_job.storage_url == "/path/to/preview.png"
    assert updated_job.render_time_ms == 123.45
    assert updated_job.validation_passed is True

    # 获取 render_job
    fetched_job = await repo.get_render_job("test_job_1")
    assert fetched_job is not None
    assert fetched_job.job_id == "test_job_1"
    assert fetched_job.status == "completed"

    # 列出场景的 render_jobs
    jobs = await repo.list_render_jobs_by_scene("scene_artifact_1")
    assert len(jobs) == 1
    assert jobs[0].job_id == "test_job_1"
