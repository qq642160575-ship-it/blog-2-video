from __future__ import annotations

from typing import Any

from domain.artifacts.service import ArtifactService
from domain.common.enums import ArtifactType
from domain.render_jobs.repository import RenderJobRepository
from generation.scene_intent.generator import SceneIntentGenerator
from generation.style_router.router import StyleRouter
from generation.llm_agents import (
    SemanticIntentExtractor,
    ThemeGenerator,
    StyleAnalyzer,
    LayoutDesigner,
)
from layout.schemas import CanvasSpec
from layout.solver import LayoutSolver
from orchestration.event_publisher import InMemoryEventPublisher
from orchestration.task_context import TaskCancelledError, TaskContext
from persistence.repositories import InMemoryArtifactRepository
from pipelines.render_preview_pipeline import RenderPreviewPipeline
from rendering.preview_renderer import MockPreviewRenderer
from rendering.visual_validator import VisualValidator
from services.workflow_service import (
    build_animation_initial_state,
    build_run_config,
    extract_update_node,
    iterate_workflow_updates,
    resolve_workflow,
)
from utils.logger import get_logger
logger = get_logger(__name__)


class WorkflowRunner:
    def __init__(
        self,
        artifact_service: ArtifactService,
        artifact_repo: InMemoryArtifactRepository,
        event_publisher: InMemoryEventPublisher,
        render_job_repo: RenderJobRepository | None = None,
        enable_rendering: bool = False,
        enable_llm_enhancement: bool = True,
        llm_confidence_threshold: float = 0.7,
    ) -> None:
        """
        Args:
            artifact_service: Artifact 服务
            artifact_repo: Artifact 仓库
            event_publisher: 事件发布器
            render_job_repo: 渲染任务仓库
            enable_rendering: 是否启用渲染
            enable_llm_enhancement: 是否启用 LLM 增强（风格分析、主题生成、语义提取、布局设计）
            llm_confidence_threshold: LLM 推荐的置信度阈值（0-1），低于此值回退到规则
        """
        self.artifact_service = artifact_service
        self.artifact_repo = artifact_repo
        self.event_publisher = event_publisher

        # 基于规则的组件（作为 fallback）
        self.style_router = StyleRouter()
        self.scene_intent_generator = SceneIntentGenerator()
        self.layout_solver = LayoutSolver()

        # LLM 增强组件（可选）
        self.enable_llm_enhancement = enable_llm_enhancement
        self.llm_confidence_threshold = llm_confidence_threshold
        if enable_llm_enhancement:
            self.style_analyzer = StyleAnalyzer(fallback_to_rules=True)
            self.theme_generator = ThemeGenerator(fallback_to_preset=True)
            self.semantic_intent_extractor = SemanticIntentExtractor(fallback_to_rules=True)
            self.layout_designer = LayoutDesigner(fallback_to_solver=True)
        else:
            self.style_analyzer = None
            self.theme_generator = None
            self.semantic_intent_extractor = None
            self.layout_designer = None

        self.canvas = CanvasSpec(
            width=1080,
            height=1920,
            safe_top=96,
            safe_right=72,
            safe_bottom=120,
            safe_left=72,
        )

        # M4: 渲染管道 (可选)
        self.enable_rendering = enable_rendering
        self.render_pipeline = None
        if enable_rendering and render_job_repo:
            renderer = MockPreviewRenderer()
            validator = VisualValidator()
            self.render_pipeline = RenderPreviewPipeline(
                renderer=renderer,
                validator=validator,
                artifact_repo=artifact_repo,
                render_job_repo=render_job_repo,
                event_publisher=event_publisher,
            )

    async def run_animation(self, context: TaskContext, script: str) -> dict[str, Any]:
        """执行动画生成完整工作流"""
        from utils.logger import get_logger
        logger = get_logger(__name__)
        logger.info(f"[Workflow] Starting animation generation for task={context.task.id}")

        try:
            # 阶段 1: 运行核心 LangGraph 工作流 (Director -> Architect -> Coder)
            core_results = await self._run_core_workflow(context, script)
            logger.info(f"[Workflow] Phase 1 (LangGraph) completed for task={context.task.id}")

            # 阶段 2: 发布初始产物 (Script, Storyboard) - 只发布一次
            initial_artifacts = await self._publish_initial_artifacts(context, script, core_results["director"])
            logger.info(f"[Workflow] Phase 2 (Initial Artifacts) published for task={context.task.id}")

            # 阶段 3: 运行 LLM 视觉增强 (Style, Theme)
            visual_strategy = await self._enhance_visual_strategy(context, script, core_results["director"])
            logger.info(f"[Workflow] Phase 3 (Visual Enhancement) completed for task={context.task.id}")

            # 阶段 4: 运行 LLM 布局增强 (Semantic, Layout)
            scene_layouts = await self._enhance_scene_layouts(context, core_results["director"], visual_strategy)
            logger.info(f"[Workflow] Phase 4 (Layout Enhancement) completed for task={context.task.id}")

            # 阶段 5: 发布最终结果
            result = await self._publish_final_results(
                context,
                core_results,
                initial_artifacts,
                visual_strategy,
                scene_layouts
            )
            logger.info(f"[Workflow] Animation generation SUCCESS for task={context.task.id}")
            return result

        except Exception as e:
            logger.error(f"[Workflow] Animation generation FAILED for task={context.task.id}: {str(e)}", exc_info=True)
            raise

    async def _run_core_workflow(self, context: TaskContext, script: str) -> dict[str, Any]:
        """运行 LangGraph 核心工作流"""
        workflow = resolve_workflow("animation")
        run_config = build_run_config(context.task.id)
        initial_state = build_animation_initial_state(script)

        # 初始进度
        await self.event_publisher.publish(
            "task.progress",
            task_id=context.task.id,
            task_run_id=context.run.id,
            session_id=context.task.session_id,
            branch_id=context.task.branch_id,
            payload={
                "node_key": "director_node",
                "label": "正在拆分镜头",
                "percent": 5,
                "completed_count": 0,
                "total_count": 3,
            },
        )

        progress_map = {
            "director_node": ("正在拆分镜头", 20, 1),
            "visual_architect_node": ("正在设计视觉方案", 40, 2),
            "coder_node": ("正在生成镜头代码", 60, 3),
        }

        # 累加器：用于在流式执行过程中手动收集最终状态，避免依赖 get_state (防止 Session 未持久化问题)
        accumulated_results = {
            "director": {},
            "visual_architect": {},
            "coder": [],
            "failed_scenes": []
        }

        async for chunk in iterate_workflow_updates(workflow, initial_state, run_config):
            await context.cancellation_token.check()
            node_name, node_data = extract_update_node(chunk)
            if node_name is None:
                continue

            normalized_node_data = self._normalize(node_data)
            
            # 手动合并状态到累加器
            if isinstance(normalized_node_data, dict):
                if "director" in normalized_node_data:
                    accumulated_results["director"] = normalized_node_data["director"]
                if "visual_architect" in normalized_node_data:
                    accumulated_results["visual_architect"] = normalized_node_data["visual_architect"]
                if "coder" in normalized_node_data:
                    # Coder 是增量列表，如果是列表则扩展，如果是单个则追加
                    new_coder = normalized_node_data["coder"]
                    if isinstance(new_coder, list):
                        accumulated_results["coder"].extend(new_coder)
                    else:
                        accumulated_results["coder"].append(new_coder)
                if "failed_scenes" in normalized_node_data:
                    accumulated_results["failed_scenes"] = normalized_node_data["failed_scenes"]

            label, percent, completed_count = progress_map.get(node_name, ("处理中", 50, 1))
            
            # 发布节点完成事件 (携带当前节点的增量数据)
            await self.event_publisher.publish(
                "workflow.node_completed",
                task_id=context.task.id,
                task_run_id=context.run.id,
                session_id=context.task.session_id,
                branch_id=context.task.branch_id,
                node_key=node_name,
                payload={"data": normalized_node_data},
            )

            # ... (进度更新与 coder_node 实时推送逻辑保持不变)
            await self.event_publisher.publish(
                "task.progress",
                task_id=context.task.id,
                task_run_id=context.run.id,
                session_id=context.task.session_id,
                branch_id=context.task.branch_id,
                node_key=node_name,
                payload={
                    "node_key": node_name,
                    "label": label,
                    "percent": percent,
                    "completed_count": completed_count,
                    "total_count": 3,
                },
            )

            if node_name == "coder_node" and isinstance(normalized_node_data, dict):
                coder_list = normalized_node_data.get("coder", [])
                for coder_item in coder_list:
                    if isinstance(coder_item, dict):
                        scene_id = coder_item.get("scene_id")
                        await self.event_publisher.publish(
                            "scene.code_generated",
                            task_id=context.task.id,
                            task_run_id=context.run.id,
                            session_id=context.task.session_id,
                            branch_id=context.task.branch_id,
                            payload={
                                "scene_id": scene_id,
                                "code": coder_item.get("code"),
                                "summary": f"场景 {scene_id} 代码生成完成",
                            },
                        )

        # 最终聚合：优先使用手动累加的值 (更健壮)
        core_results = {
            "director": accumulated_results["director"] or {},
            "visual_architect": accumulated_results["visual_architect"] or {},
            "coder": accumulated_results["coder"] or [],
            "failed_scenes": accumulated_results["failed_scenes"] or [],
        }
        
        # 记录关键日志，用于确认 Phase 1 结束时的产物数量
        director_data = core_results["director"]
        scene_count = len(director_data.get("scenes", [])) if isinstance(director_data, dict) else 0
        logger.info(f"[Workflow] Phase 1 (Core) finished. Harvested scenes={scene_count}")
        return core_results

    async def _publish_initial_artifacts(self, context: TaskContext, script: str, director: dict) -> dict[str, Any]:
        """发布初始阶段的产物"""
        script_artifact = await self.artifact_service.publish_artifact(
            session_id=context.task.session_id,
            branch_id=context.task.branch_id,
            task_id=context.task.id,
            artifact_type=ArtifactType.SCRIPT,
            content_text=script,
            summary="源脚本文本",
        )

        storyboard_artifact = await self.artifact_service.publish_artifact(
            session_id=context.task.session_id,
            branch_id=context.task.branch_id,
            task_id=context.task.id,
            artifact_type=ArtifactType.STORYBOARD,
            content_json=director,
            summary="全局分镜脚本",
            parent_artifact_id=script_artifact.id,
        )

        # 发布事件供前端即时更新
        await self.event_publisher.publish(
            "artifact.published",
            task_id=context.task.id,
            task_run_id=context.run.id,
            session_id=context.task.session_id,
            branch_id=context.task.branch_id,
            payload={
                "artifact_id": storyboard_artifact.id,
                "artifact_type": "storyboard",
                "summary": "分镜脚本已生成",
                "scene_count": len(director.get("scenes", [])),
            },
        )

        return {
            "script_artifact": script_artifact,
            "storyboard_artifact": storyboard_artifact,
        }

    async def _enhance_visual_strategy(self, context: TaskContext, script: str, director: dict) -> Any:
        """视觉策略增强 (Style & Theme)"""
        director_scenes = director.get("scenes", [])
        storyboard = {"scenes": director_scenes}

        await self.event_publisher.publish(
            "task.progress",
            task_id=context.task.id,
            task_run_id=context.run.id,
            session_id=context.task.session_id,
            branch_id=context.task.branch_id,
            payload={
                "node_key": "style_analysis",
                "label": "正在分析视觉风格",
                "percent": 65,
            },
        )

        if not self.enable_llm_enhancement or not self.style_analyzer:
            logger.info("[Workflow] LLM enhancement disabled or style_analyzer missing. Using rules.")
            return self.style_router.route(storyboard, None)

        try:
            # 风格选择
            style_rec = await self.style_analyzer.analyze(script, storyboard, None)
            rule_based = self.style_router.route(storyboard, None)

            if self.style_analyzer.should_use_llm_recommendation(style_rec, rule_based.style_family):
                style_family = style_rec.style_family
                style_source = "llm"
                logger.info(f"[Workflow] Using LLM recommended style: {style_family} (Confidence: {style_rec.confidence})")
            else:
                style_family = rule_based.style_family
                style_source = "rules"
                logger.info(f"[Workflow] LLM style confidence low. Falling back to rules: {style_family}")

            # 主题生成
            if self.theme_generator and style_rec.confidence >= self.llm_confidence_threshold:
                theme_profile = await self.theme_generator.generate(
                    style_family=style_family,
                    script=script,
                    brand_colors=style_rec.color_suggestions or None,
                )
                theme_source = "llm"
                logger.info("[Workflow] Using LLM generated theme colors.")
            else:
                from generation.style_router.profiles import get_theme_profile
                theme_profile = get_theme_profile(style_family)
                theme_source = "preset"
                logger.info("[Workflow] Using preset theme.")

            # 构建增强策略
            from generation.style_router.profiles import VisualStrategy
            strategy = VisualStrategy(
                style_family=style_family,
                theme_profile=theme_profile,
                motion_profile=rule_based.motion_profile,
                asset_policy=rule_based.asset_policy,
                scene_type_mapping=rule_based.scene_type_mapping,
            )
            # 注意：VisualStrategy BaseModel 通常不带 metadata 字段，除非显式设置 extra='allow'
            # 我们在这里通过本地变量传递元数据，或者如果后续发布需要，直接传给发布方法
            setattr(strategy, "_llm_metadata", {
                "style_source": style_source,
                "theme_source": theme_source,
                "llm_recommendation": style_rec.model_dump() if hasattr(style_rec, "model_dump") else str(style_rec),
            })
            return strategy

        except Exception as e:
            logger.error(f"[Workflow] Visual enhancement LLM error: {str(e)}. Falling back to rules.")
            return self.style_router.route(storyboard, None)

    async def _enhance_scene_layouts(self, context: TaskContext, director: dict, strategy: Any) -> dict[str, dict]:
        """关键语义提取与布局设计增强 (Semantic & Layout)"""
        scenes = director.get("scenes", [])
        scene_layouts = {}
        total = len(scenes)

        for idx, scene in enumerate(scenes, 1):
            if not isinstance(scene, dict): continue
            scene_id = str(scene.get("scene_id", f"scene_{idx}"))
            scene_type = self._infer_scene_type(scene)

            await self.event_publisher.publish(
                "task.progress",
                task_id=context.task.id,
                task_run_id=context.run.id,
                session_id=context.task.session_id,
                branch_id=context.task.branch_id,
                payload={
                    "node_key": "layout_generation",
                    "label": f"正在优化镜头布局 ({idx}/{total})",
                    "percent": 70 + int(15 * idx / total),
                    "completed_count": idx,
                    "total_count": total,
                },
            )

            try:
                scene_ctx = {**scene, "scene_type": scene_type}
                # 语义提取
                if self.enable_llm_enhancement and self.semantic_intent_extractor:
                    intents = await self.semantic_intent_extractor.extract(scene_ctx, strategy.model_dump())
                    intent_source = "llm"
                else:
                    intents = self.scene_intent_generator.generate(scene_ctx, strategy.model_dump())
                    intent_source = "rules"

                # 布局设计
                if self.enable_llm_enhancement and self.layout_designer:
                    layout_spec = await self.layout_designer.design(scene_ctx, intents, self.canvas, strategy.model_dump())
                    layout_source = "llm"
                else:
                    layout_spec = self.layout_solver.solve(intents, self.canvas, scene_type)
                    layout_source = "template"

                layout_spec.scene_id = scene_id
                layout_spec.metadata = {
                    "intent_source": intent_source,
                    "layout_source": layout_source,
                }
                scene_layouts[scene_id] = layout_spec.model_dump()
                
                # [NEW] 实时发布布局更新事件，让前端即时显示优化结果
                await self.event_publisher.publish(
                    "scene.layout_generated",
                    task_id=context.task.id,
                    task_run_id=context.run.id,
                    session_id=context.task.session_id,
                    branch_id=context.task.branch_id,
                    payload={
                        "scene_id": scene_id,
                        "layout_spec": scene_layouts[scene_id],
                        "summary": f"场景 {scene_id} 布局优化完成 ({layout_source})",
                    },
                )
                logger.info(f"[Workflow] Scene {scene_id} layout SUCCESS (Intent: {intent_source}, Layout: {layout_source})")

            except Exception as e:
                logger.warning(f"[Workflow] Scene {scene_id} LLM enhancement failed: {str(e)}. Using fallback.")
                # Fallback
                intents = self.scene_intent_generator.generate({**scene, "scene_type": scene_type}, strategy.model_dump())
                layout_spec = self.layout_solver.solve(intents, self.canvas, scene_type)
                layout_spec.scene_id = scene_id
                layout_spec.metadata = {"layout_source": "fallback", "error": str(e)}
                scene_layouts[scene_id] = layout_spec.model_dump()

        return scene_layouts


    async def _publish_final_results(
        self,
        context: TaskContext,
        core_results: dict,
        initial_artifacts: dict,
        visual_strategy: Any,
        scene_layouts: dict
    ) -> dict[str, Any]:
        """发布并聚合最终结果"""
        script_art = initial_artifacts["script_artifact"]
        storyboard_art = initial_artifacts["storyboard_artifact"]
        director_scenes = core_results["director"].get("scenes", [])
        coder_results = core_results["coder"]
        failed_scenes = core_results["failed_scenes"]

        # 1. 发布增强的视觉策略
        visual_strategy_content = {
            "style_family": visual_strategy.style_family,
            "theme_profile": visual_strategy.theme_profile.model_dump(),
            "motion_profile": visual_strategy.motion_profile.model_dump(),
            "asset_policy": visual_strategy.asset_policy.model_dump(),
            "scene_type_mapping": {
                k: v.model_dump() for k, v in visual_strategy.scene_type_mapping.items()
            },
            "llm_metadata": getattr(visual_strategy, "_llm_metadata", {}),
        }

        visual_artifact = await self.artifact_service.publish_artifact(
            session_id=context.task.session_id,
            branch_id=context.task.branch_id,
            task_id=context.task.id,
            artifact_type=ArtifactType.VISUAL_STRATEGY,
            content_json=visual_strategy_content,
            summary=f"增强视觉策略 ({visual_strategy.style_family})",
            parent_artifact_id=storyboard_art.id,
        )

        # 2. 发布布局 Bundle
        layout_bundle_artifact = await self.artifact_service.publish_artifact(
            session_id=context.task.session_id,
            branch_id=context.task.branch_id,
            task_id=context.task.id,
            artifact_type=ArtifactType.SCENE_LAYOUT_BUNDLE,
            content_json={"scene_layouts": scene_layouts},
            summary=f"生成 {len(scene_layouts)} 个场景布局",
            parent_artifact_id=visual_artifact.id,
        )

        # 3. 发布代码 Bundle
        code_bundle = {"scenes": coder_results, "failed_scenes": failed_scenes}
        code_artifact = await self.artifact_service.publish_artifact(
            session_id=context.task.session_id,
            branch_id=context.task.branch_id,
            task_id=context.task.id,
            artifact_type=ArtifactType.SCENE_CODE_BUNDLE,
            content_json=code_bundle,
            summary="场景代码 Bundle",
            parent_artifact_id=layout_bundle_artifact.id,
        )

        # 4. 发布具体场景 Artifacts
        coder_by_scene = {
            item.get("scene_id"): item
            for item in coder_results if isinstance(item, dict) and item.get("scene_id")
        }
        scene_artifact_ids: list[str] = []

        for index, scene in enumerate(director_scenes, start=1):
            if not isinstance(scene, dict): continue
            scene_id = str(scene.get("scene_id") or f"scene_{index}")
            scene_type = self._infer_scene_type(scene)
            coder_result = coder_by_scene.get(scene_id, {})
            layout_spec = scene_layouts.get(scene_id)

            scene_artifact = await self.artifact_service.publish_scene_artifact(
                bundle_artifact=code_artifact,
                scene_id=scene_id,
                scene_order=index,
                scene_type=scene_type,
                script_text=scene.get("script"),
                visual_intent={
                    "scene": scene,
                    "theme": visual_strategy_content["theme_profile"],
                    "primitives": visual_strategy_content.get("scene_type_mapping", {}).get(scene_type, {}).get("allowed_primitives", []),
                },
                layout_spec=layout_spec,
                code_text=coder_result.get("code"),
                validation_report={
                    "passed": scene_id not in failed_scenes,
                    "issues": [] if scene_id not in failed_scenes else ["qa_guard_failed"],
                },
                status="failed" if scene_id in failed_scenes else "ready",
            )
            scene_artifact_ids.append(scene_artifact.id)

        # 5. 渲染预览 (可选)
        if self.enable_rendering and self.render_pipeline:
            await self.event_publisher.publish(
                "task.progress",
                task_id=context.task.id, task_run_id=context.run.id,
                session_id=context.task.session_id, branch_id=context.task.branch_id,
                payload={"node_key": "render_preview", "label": "正在渲染场景预览", "percent": 95},
            )
            await self.render_pipeline.render_all_scenes(
                scene_artifact_ids=scene_artifact_ids,
                task_id=context.task.id, session_id=context.task.session_id,
                branch_id=context.task.branch_id, task_run_id=context.run.id,
                frame=0, validate=True,
            )

        # 6. 发布验证报告
        validation_report = {
            "passed": not failed_scenes,
            "error_count": len(failed_scenes),
            "failed_scenes": failed_scenes,
        }
        validation_artifact = await self.artifact_service.publish_artifact(
            session_id=context.task.session_id,
            branch_id=context.task.branch_id,
            task_id=context.task.id,
            artifact_type=ArtifactType.VALIDATION_REPORT,
            content_json=validation_report,
            summary="流程验证报告",
            parent_artifact_id=code_artifact.id,
        )

        # 7. 全局事件通告完成
        await self.event_publisher.publish(
            "artifact.published",
            task_id=context.task.id, task_run_id=context.run.id,
            session_id=context.task.session_id, branch_id=context.task.branch_id,
            payload={
                "artifact_id": code_artifact.id,
                "artifact_type": "scene_code_bundle",
                "summary": "全流程生成完成",
                "scene_count": len(scene_artifact_ids),
            },
        )

        return {
            "artifact_ids": [
                script_art.id, storyboard_art.id, visual_artifact.id,
                layout_bundle_artifact.id, code_artifact.id, validation_artifact.id
            ],
            "scene_artifact_ids": scene_artifact_ids,
            "failed_scenes": failed_scenes,
        }

    @staticmethod
    def _infer_scene_type(scene: dict[str, Any]) -> str:
        script = str(scene.get("script") or "")
        if "对比" in script:
            return "contrast"
        if "步骤" in script or "首先" in script:
            return "process"
        if any(char.isdigit() for char in script):
            return "data_point"
        return "statement"

    @staticmethod
    def _normalize(value: Any) -> Any:
        if isinstance(value, list):
            return [WorkflowRunner._normalize(item) for item in value]
        if isinstance(value, dict):
            return {key: WorkflowRunner._normalize(item) for key, item in value.items()}
        if hasattr(value, "model_dump"):
            return WorkflowRunner._normalize(value.model_dump())
        return value
