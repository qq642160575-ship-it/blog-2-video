import pytest

from domain.artifacts.service import ArtifactService
from domain.render_jobs.repository import RenderJobRepository
from orchestration.event_publisher import InMemoryEventPublisher
from orchestration.task_context import TaskContext
from orchestration.workflow_runner import WorkflowRunner
from persistence.repositories import InMemoryArtifactRepository
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker


@pytest.fixture
async def db_session():
    """创建测试数据库会话"""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async_session_maker = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session_maker() as session:
        yield session


@pytest.fixture
def artifact_repo():
    return InMemoryArtifactRepository()


@pytest.fixture
def event_publisher():
    return InMemoryEventPublisher()


@pytest.fixture
def artifact_service(artifact_repo, event_publisher):
    return ArtifactService(artifact_repo, event_publisher)


@pytest.fixture
async def render_job_repo(db_session):
    return RenderJobRepository(db_session)


@pytest.mark.asyncio
async def test_m4_rendering_integration(artifact_service, artifact_repo, event_publisher, db_session):
    """测试 M4 渲染集成"""
    render_job_repo = RenderJobRepository(db_session)

    # 创建启用渲染的 WorkflowRunner
    runner = WorkflowRunner(
        artifact_service=artifact_service,
        artifact_repo=artifact_repo,
        event_publisher=event_publisher,
        render_job_repo=render_job_repo,
        enable_rendering=True,
    )

    # 验证渲染管道已初始化
    assert runner.enable_rendering is True
    assert runner.render_pipeline is not None

    # 创建测试上下文
    from domain.tasks.entities import Task, TaskRun
    from orchestration.task_context import CancellationToken

    task = Task(
        id="test_task_1",
        session_id="test_session",
        branch_id="test_branch",
        task_type="create_video",
        input_data={"script": "测试脚本"},
        status="running",
    )
    task_run = TaskRun(id="test_run_1", task_id=task.id, status="running")
    context = TaskContext(
        task=task,
        run=task_run,
        cancellation_token=CancellationToken(),
    )

    # 运行工作流
    script = "这是一个测试视频。第一个场景介绍产品。第二个场景展示数据。"
    result = await runner.run_animation(context, script)

    # 验证基本结果
    assert "artifact_ids" in result
    assert "scene_artifact_ids" in result
    assert len(result["scene_artifact_ids"]) > 0

    # 验证场景 artifacts 包含 preview_image_url
    for scene_artifact_id in result["scene_artifact_ids"]:
        scene_artifact = await artifact_repo.get_artifact(scene_artifact_id)
        assert scene_artifact is not None

        # 检查是否有 preview_image_url (渲染后应该有)
        content = scene_artifact.content
        if runner.enable_rendering:
            assert "preview_image_url" in content
            assert content["preview_image_url"] is not None
            assert "preview_metadata" in content


@pytest.mark.asyncio
async def test_m4_rendering_disabled(artifact_service, artifact_repo, event_publisher):
    """测试禁用渲染时的行为"""
    # 创建未启用渲染的 WorkflowRunner
    runner = WorkflowRunner(
        artifact_service=artifact_service,
        artifact_repo=artifact_repo,
        event_publisher=event_publisher,
        enable_rendering=False,
    )

    # 验证渲染管道未初始化
    assert runner.enable_rendering is False
    assert runner.render_pipeline is None

    # 创建测试上下文
    from domain.tasks.entities import Task, TaskRun
    from orchestration.task_context import CancellationToken

    task = Task(
        id="test_task_2",
        session_id="test_session",
        branch_id="test_branch",
        task_type="create_video",
        input_data={"script": "测试脚本"},
        status="running",
    )
    task_run = TaskRun(id="test_run_2", task_id=task.id, status="running")
    context = TaskContext(
        task=task,
        run=task_run,
        cancellation_token=CancellationToken(),
    )

    # 运行工作流
    script = "这是一个测试视频。第一个场景介绍产品。"
    result = await runner.run_animation(context, script)

    # 验证基本结果
    assert "artifact_ids" in result
    assert "scene_artifact_ids" in result

    # 验证场景 artifacts 不包含 preview_image_url (因为渲染被禁用)
    for scene_artifact_id in result["scene_artifact_ids"]:
        scene_artifact = await artifact_repo.get_artifact(scene_artifact_id)
        assert scene_artifact is not None

        content = scene_artifact.content
        # 禁用渲染时不应该有 preview_image_url
        assert "preview_image_url" not in content or content.get("preview_image_url") is None


@pytest.mark.asyncio
async def test_render_preview_pipeline_directly(artifact_repo, event_publisher, db_session):
    """直接测试 RenderPreviewPipeline"""
    from pipelines.render_preview_pipeline import RenderPreviewPipeline
    from rendering.preview_renderer import MockPreviewRenderer
    from rendering.visual_validator import VisualValidator

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
    from domain.artifacts.entities import ArtifactRecord
    from datetime import datetime

    scene_artifact = ArtifactRecord(
        id="test_scene_artifact_1",
        artifact_id="test_scene_artifact_1",
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
        scene_artifact_id="test_scene_artifact_1",
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
    updated_artifact = await artifact_repo.get_artifact("test_scene_artifact_1")
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
