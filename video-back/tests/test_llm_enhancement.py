"""测试 LLM 增强的视频生成流程"""

import pytest

from config.llm_enhancement_config import (
    BALANCED_CONFIG,
    CONSERVATIVE_CONFIG,
    AGGRESSIVE_CONFIG,
    DISABLED_CONFIG,
)


def test_llm_enhancement_config():
    """测试 LLM 增强配置"""
    # 平衡模式
    assert BALANCED_CONFIG.is_enabled is True
    assert BALANCED_CONFIG.is_hybrid_mode is True
    assert BALANCED_CONFIG.confidence_threshold == 0.7

    # 禁用模式
    assert DISABLED_CONFIG.is_enabled is False
    assert DISABLED_CONFIG.mode == "disabled"

    # 激进模式
    assert AGGRESSIVE_CONFIG.is_full_mode is True
    assert AGGRESSIVE_CONFIG.confidence_threshold == 0.5


@pytest.mark.asyncio
async def test_semantic_intent_extractor():
    """测试语义意图提取器"""
    from generation.llm_agents import SemanticIntentExtractor

    extractor = SemanticIntentExtractor(fallback_to_rules=True)

    scene = {
        "scene_id": "scene_1",
        "scene_type": "statement",
        "script": "我们的产品帮助企业提升效率 50%\n节省成本，提高产出",
    }

    intents = await extractor.extract(scene, None)

    # 验证提取了意图
    assert len(intents) > 0

    # 验证意图包含必要字段
    for intent in intents:
        assert intent.id is not None
        assert intent.role is not None
        assert intent.primitive_type is not None
        assert intent.importance >= 1 and intent.importance <= 100
        assert intent.text is not None


@pytest.mark.asyncio
async def test_theme_generator():
    """测试主题生成器"""
    from generation.llm_agents import ThemeGenerator

    generator = ThemeGenerator(fallback_to_preset=True)

    script = "这是一个关于科技创新的视频，介绍我们的 AI 产品如何改变行业。"

    theme = await generator.generate(
        style_family="product_ui",
        script=script,
        brand_colors=["#0066FF"],
        user_preference=None,
    )

    # 验证主题包含必要字段
    assert theme.background is not None
    assert theme.primary_accent is not None
    assert theme.secondary_accent is not None
    assert theme.text_main is not None
    assert theme.font_family_primary is not None
    assert theme.base_font_size >= 12


@pytest.mark.asyncio
async def test_style_analyzer():
    """测试风格分析器"""
    from generation.llm_agents import StyleAnalyzer

    analyzer = StyleAnalyzer(fallback_to_rules=True)

    script = "数据显示，我们的用户增长了 300%，收入提升了 5 倍。"
    storyboard = {
        "scenes": [
            {"scene_id": "scene_1", "scene_type": "data_point", "script": script}
        ]
    }

    recommendation = await analyzer.analyze(script, storyboard, None)

    # 验证推荐结果
    assert recommendation.style_family in [
        "minimal_light",
        "diagrammatic_minimal",
        "product_ui",
        "editorial_typography",
    ]
    assert recommendation.confidence >= 0 and recommendation.confidence <= 1
    assert recommendation.reasoning is not None
    assert recommendation.target_audience is not None


@pytest.mark.asyncio
async def test_layout_designer():
    """测试布局设计器"""
    from generation.llm_agents import LayoutDesigner
    from layout.schemas import CanvasSpec
    from layout.primitives import PrimitiveIntent

    designer = LayoutDesigner(fallback_to_solver=True)

    canvas = CanvasSpec(
        width=1080,
        height=1920,
        safe_top=96,
        safe_right=72,
        safe_bottom=120,
        safe_left=72,
    )

    scene = {
        "scene_id": "scene_1",
        "scene_type": "statement",
        "script": "欢迎使用我们的产品",
    }

    intents = [
        PrimitiveIntent(
            id="scene_1_title",
            role="title",
            primitive_type="HeroTitle",
            importance=100,
            text="欢迎使用我们的产品",
            preferred_region="top",
        )
    ]

    layout_spec = await designer.design(scene, intents, canvas, None)

    # 验证布局规格
    assert layout_spec.scene_id == "scene_1"
    assert layout_spec.canvas == canvas
    assert len(layout_spec.elements) > 0

    # 验证元素包含必要字段
    for element in layout_spec.elements:
        assert element.id is not None
        assert element.primitive_type is not None
        assert element.box is not None
        assert "x" in element.box
        assert "y" in element.box
        assert "width" in element.box
        assert "height" in element.box


@pytest.mark.asyncio
async def test_workflow_runner_with_llm_enhancement(
    artifact_service, artifact_repo, event_publisher
):
    """测试启用 LLM 增强的 WorkflowRunner"""
    from orchestration.workflow_runner import WorkflowRunner
    from orchestration.task_context import TaskContext, CancellationToken
    from domain.tasks.entities import Task, TaskRun

    # 创建启用 LLM 增强的 WorkflowRunner
    runner = WorkflowRunner(
        artifact_service=artifact_service,
        artifact_repo=artifact_repo,
        event_publisher=event_publisher,
        enable_rendering=False,
        enable_llm_enhancement=True,
        llm_confidence_threshold=0.7,
    )

    # 验证 LLM 组件已初始化
    assert runner.enable_llm_enhancement is True
    assert runner.style_analyzer is not None
    assert runner.theme_generator is not None
    assert runner.semantic_intent_extractor is not None
    assert runner.layout_designer is not None

    # 创建测试上下文
    task = Task(
        id="test_task_llm",
        session_id="test_session",
        branch_id="test_branch",
        task_type="create_video",
        input_data={"script": "测试脚本"},
        status="running",
    )
    task_run = TaskRun(id="test_run_llm", task_id=task.id, status="running")
    context = TaskContext(
        task=task,
        run=task_run,
        cancellation_token=CancellationToken(),
    )

    # 运行工作流
    script = "这是一个测试视频。第一个场景介绍产品，数据显示增长 50%。"
    result = await runner.run_animation(context, script)

    # 验证结果
    assert "artifact_ids" in result
    assert "scene_artifact_ids" in result

    # 验证 visual_strategy artifact 包含 LLM 元数据
    visual_artifacts = [
        aid for aid in result["artifact_ids"]
        if aid.startswith("visual_strategy")
    ]
    if visual_artifacts:
        visual_artifact = await artifact_repo.get_artifact(visual_artifacts[0])
        assert "llm_metadata" in visual_artifact.content
        llm_metadata = visual_artifact.content["llm_metadata"]
        assert "style_source" in llm_metadata
        assert "theme_source" in llm_metadata


@pytest.mark.asyncio
async def test_workflow_runner_without_llm_enhancement(
    artifact_service, artifact_repo, event_publisher
):
    """测试禁用 LLM 增强的 WorkflowRunner（纯规则模式）"""
    from orchestration.workflow_runner import WorkflowRunner
    from orchestration.task_context import TaskContext, CancellationToken
    from domain.tasks.entities import Task, TaskRun

    # 创建禁用 LLM 增强的 WorkflowRunner
    runner = WorkflowRunner(
        artifact_service=artifact_service,
        artifact_repo=artifact_repo,
        event_publisher=event_publisher,
        enable_rendering=False,
        enable_llm_enhancement=False,
    )

    # 验证 LLM 组件未初始化
    assert runner.enable_llm_enhancement is False
    assert runner.style_analyzer is None
    assert runner.theme_generator is None
    assert runner.semantic_intent_extractor is None
    assert runner.layout_designer is None

    # 创建测试上下文
    task = Task(
        id="test_task_no_llm",
        session_id="test_session",
        branch_id="test_branch",
        task_type="create_video",
        input_data={"script": "测试脚本"},
        status="running",
    )
    task_run = TaskRun(id="test_run_no_llm", task_id=task.id, status="running")
    context = TaskContext(
        task=task,
        run=task_run,
        cancellation_token=CancellationToken(),
    )

    # 运行工作流
    script = "这是一个测试视频。第一个场景介绍产品。"
    result = await runner.run_animation(context, script)

    # 验证结果
    assert "artifact_ids" in result
    assert "scene_artifact_ids" in result

    # 验证 visual_strategy artifact 使用规则模式
    visual_artifacts = [
        aid for aid in result["artifact_ids"]
        if aid.startswith("visual_strategy")
    ]
    if visual_artifacts:
        visual_artifact = await artifact_repo.get_artifact(visual_artifacts[0])
        llm_metadata = visual_artifact.content.get("llm_metadata", {})
        assert llm_metadata.get("style_source") == "rules"
        assert llm_metadata.get("theme_source") == "preset"


@pytest.fixture
def artifact_service(artifact_repo, event_publisher):
    from domain.artifacts.service import ArtifactService
    return ArtifactService(artifact_repo, event_publisher)


@pytest.fixture
def artifact_repo():
    from persistence.repositories import InMemoryArtifactRepository
    return InMemoryArtifactRepository()


@pytest.fixture
def event_publisher():
    from orchestration.event_publisher import InMemoryEventPublisher
    return InMemoryEventPublisher()
