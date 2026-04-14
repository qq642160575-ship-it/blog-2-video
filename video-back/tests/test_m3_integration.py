import asyncio

import pytest

import app.dependencies as deps
from api.routes import create_session, create_task, get_artifact, list_branch_artifacts
from api.schemas import CreateSessionRequest, CreateTaskRequest
from app.dependencies import AppContainer
from domain.common.enums import ArtifactType, TaskType
from orchestration.task_context import PipelineResult


class FakeM3Pipeline:
    """模拟 M3 流程的 pipeline,用于测试"""

    name = "create_video"

    def __init__(self, container: AppContainer) -> None:
        self.container = container

    async def run(self, context):
        # 模拟生成 storyboard
        storyboard = {
            "scenes": [
                {"scene_id": "scene_1", "script": "这是第一个场景", "scene_type": "statement"},
                {"scene_id": "scene_2", "script": "数据显示增长了50%", "scene_type": "data_point"},
                {"scene_id": "scene_3", "script": "传统方法 vs 新方法", "scene_type": "contrast"},
            ]
        }

        storyboard_artifact = await self.container.artifact_service.publish_artifact(
            session_id=context.task.session_id,
            branch_id=context.task.branch_id,
            task_id=context.task.id,
            artifact_type=ArtifactType.STORYBOARD,
            content_json=storyboard,
            summary="测试分镜",
        )

        # 模拟 style_router 生成视觉策略
        visual_strategy = {
            "style_family": "minimal_light",
            "theme_profile": {
                "theme_id": "minimal_light",
                "name": "简约明亮",
                "color_primary": "#000000",
            },
        }

        visual_artifact = await self.container.artifact_service.publish_artifact(
            session_id=context.task.session_id,
            branch_id=context.task.branch_id,
            task_id=context.task.id,
            artifact_type=ArtifactType.VISUAL_STRATEGY,
            content_json=visual_strategy,
            summary="测试视觉策略",
            parent_artifact_id=storyboard_artifact.id,
        )

        # 模拟 layout_solver 生成布局
        scene_layouts = {
            "scene_1": {
                "scene_id": "scene_1",
                "canvas": {"width": 1080, "height": 1920},
                "elements": [
                    {
                        "id": "scene_1_title",
                        "primitive_type": "HeroTitle",
                        "role": "title",
                        "box": {"x": 100, "y": 200, "width": 880, "height": 150},
                    }
                ],
            },
            "scene_2": {
                "scene_id": "scene_2",
                "canvas": {"width": 1080, "height": 1920},
                "elements": [
                    {
                        "id": "scene_2_stat",
                        "primitive_type": "StatPanel",
                        "role": "stat",
                        "box": {"x": 100, "y": 300, "width": 880, "height": 200},
                    }
                ],
            },
            "scene_3": {
                "scene_id": "scene_3",
                "canvas": {"width": 1080, "height": 1920},
                "elements": [
                    {
                        "id": "scene_3_left",
                        "primitive_type": "BodyCard",
                        "role": "comparison_left",
                        "box": {"x": 50, "y": 300, "width": 450, "height": 300},
                    },
                    {
                        "id": "scene_3_right",
                        "primitive_type": "BodyCard",
                        "role": "comparison_right",
                        "box": {"x": 550, "y": 300, "width": 450, "height": 300},
                    },
                ],
            },
        }

        layout_artifact = await self.container.artifact_service.publish_artifact(
            session_id=context.task.session_id,
            branch_id=context.task.branch_id,
            task_id=context.task.id,
            artifact_type=ArtifactType.SCENE_LAYOUT_BUNDLE,
            content_json={"scene_layouts": scene_layouts},
            summary="测试场景布局",
            parent_artifact_id=visual_artifact.id,
        )

        return PipelineResult(
            summary={"scene_count": 3, "style_family": "minimal_light"},
            artifact_ids=[storyboard_artifact.id, visual_artifact.id, layout_artifact.id],
            scene_artifact_ids=[],
        )


@pytest.fixture
async def m3_container(monkeypatch):
    container = AppContainer(use_real_workflow=False)
    container.dispatcher._pipelines[TaskType.CREATE_VIDEO] = FakeM3Pipeline(container)
    monkeypatch.setattr(deps, "_container", container)
    await container.start()
    try:
        yield container
    finally:
        await container.stop()


@pytest.mark.anyio
async def test_m3_integration_generates_layout_artifacts(m3_container):
    """测试 M3 集成是否正确生成 layout artifacts"""
    session_response = await create_session(
        CreateSessionRequest(
            source_type="text",
            source_content="测试 M3 集成",
            title="M3 测试",
        )
    )
    branch_id = session_response.branch_id
    session_id = session_response.session_id

    artifacts_response = await list_branch_artifacts(branch_id)
    source_artifact_id = artifacts_response["items"][0]["artifact_id"]

    task_response = await create_task(
        session_id,
        CreateTaskRequest(
            branch_id=branch_id,
            task_type=TaskType.CREATE_VIDEO,
            request_payload={"source_artifact_id": source_artifact_id},
            baseline_artifact_id=None,
        ),
    )
    task_id = task_response.task_id

    # 等待任务完成
    for _ in range(40):
        from api.routes import get_task

        task_payload = await get_task(task_id)
        if task_payload["status"] == "succeeded":
            break
        await asyncio.sleep(0.05)

    assert task_payload["status"] == "succeeded"

    # 验证生成了正确的 artifacts
    artifacts_response = await list_branch_artifacts(branch_id)
    artifacts = artifacts_response["items"]

    artifact_types = [item["artifact_type"] for item in artifacts]
    assert ArtifactType.STORYBOARD in artifact_types
    assert ArtifactType.VISUAL_STRATEGY in artifact_types
    assert ArtifactType.SCENE_LAYOUT_BUNDLE in artifact_types

    # 验证 layout artifact 的内容
    layout_artifact = next(
        item for item in artifacts if item["artifact_type"] == ArtifactType.SCENE_LAYOUT_BUNDLE
    )
    layout_content = layout_artifact["content_json"]
    assert "scene_layouts" in layout_content
    assert len(layout_content["scene_layouts"]) == 3
    assert "scene_1" in layout_content["scene_layouts"]
    assert "scene_2" in layout_content["scene_layouts"]
    assert "scene_3" in layout_content["scene_layouts"]

    # 验证每个场景的布局包含 elements
    scene_1_layout = layout_content["scene_layouts"]["scene_1"]
    assert "elements" in scene_1_layout
    assert len(scene_1_layout["elements"]) > 0
    assert scene_1_layout["elements"][0]["primitive_type"] == "HeroTitle"

    scene_2_layout = layout_content["scene_layouts"]["scene_2"]
    assert scene_2_layout["elements"][0]["primitive_type"] == "StatPanel"

    scene_3_layout = layout_content["scene_layouts"]["scene_3"]
    assert len(scene_3_layout["elements"]) == 2  # 对比场景有两个元素


@pytest.mark.anyio
async def test_m3_visual_strategy_contains_theme_profile(m3_container):
    """测试 M3 视觉策略包含主题配置"""
    session_response = await create_session(
        CreateSessionRequest(
            source_type="text",
            source_content="测试视觉策略",
            title="视觉策略测试",
        )
    )
    branch_id = session_response.branch_id
    session_id = session_response.session_id

    artifacts_response = await list_branch_artifacts(branch_id)
    source_artifact_id = artifacts_response["items"][0]["artifact_id"]

    task_response = await create_task(
        session_id,
        CreateTaskRequest(
            branch_id=branch_id,
            task_type=TaskType.CREATE_VIDEO,
            request_payload={"source_artifact_id": source_artifact_id},
        ),
    )

    # 等待任务完成
    for _ in range(40):
        from api.routes import get_task

        task_payload = await get_task(task_response.task_id)
        if task_payload["status"] == "succeeded":
            break
        await asyncio.sleep(0.05)

    # 获取视觉策略 artifact
    artifacts_response = await list_branch_artifacts(branch_id)
    visual_artifact = next(
        item
        for item in artifacts_response["items"]
        if item["artifact_type"] == ArtifactType.VISUAL_STRATEGY
    )

    visual_content = visual_artifact["content_json"]
    assert "style_family" in visual_content
    assert "theme_profile" in visual_content
    assert visual_content["style_family"] == "minimal_light"
    assert visual_content["theme_profile"]["theme_id"] == "minimal_light"
