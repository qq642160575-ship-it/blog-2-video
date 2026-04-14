from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from layout.schemas import CanvasSpec, LayoutElement, SceneLayoutSpec
from models.get_model import get_model
from utils.structured_output import ainvoke_structured


class LayoutElementSpec(BaseModel):
    """LLM 设计的布局元素"""
    element_id: str = Field(description="元素 ID")
    element_type: str = Field(description="元素类型：title, body, stat, quote, image, icon, decoration")
    primitive_type: str = Field(description="视觉组件类型：HeroTitle, BodyCard, StatPanel 等")
    position_x: int = Field(description="X 坐标（px）", ge=0)
    position_y: int = Field(description="Y 坐标（px）", ge=0)
    width: int = Field(description="宽度（px）", ge=2)
    height: int = Field(description="高度（px）", ge=2)
    z_index: int = Field(description="层级 0-100", ge=0, le=100)
    reveal_order: int = Field(description="出场顺序 0-10", ge=0, le=10)
    text_content: str | None = Field(default=None, description="文本内容")
    style_notes: str = Field(description="样式说明")
    animation_notes: str = Field(description="动画说明")


class LayoutDesignResult(BaseModel):
    """布局设计结果"""
    elements: list[LayoutElementSpec] = Field(description="布局元素列表")
    composition: str = Field(description="构图方式：centered, asymmetric, grid, split, layered")
    visual_hierarchy: list[str] = Field(description="视觉层级（element_id 列表）")
    focal_point: str = Field(description="视觉焦点元素 ID")
    design_reasoning: str = Field(description="设计理由")
    estimated_density: str = Field(description="布局密度：sparse, medium, dense")


class LayoutDesigner:
    """LLM 驱动的布局设计器

    使用 LLM 理解场景内容，生成创意布局，而不是套用固定模板。
    """

    def __init__(self, fallback_to_solver: bool = True):
        """
        Args:
            fallback_to_solver: 如果 LLM 调用失败，是否回退到基于模板的布局求解
        """
        self.model = get_model("visual_architect")
        self.fallback_to_solver = fallback_to_solver

    async def design(
        self,
        scene: dict[str, Any],
        intents: list[Any],
        canvas: CanvasSpec,
        visual_strategy: dict[str, Any] | None = None,
    ) -> SceneLayoutSpec:
        """设计场景布局

        Args:
            scene: 场景数据
            intents: 视觉意图列表（PrimitiveIntent）
            canvas: 画布规格
            visual_strategy: 视觉策略

        Returns:
            SceneLayoutSpec
        """
        scene_id = scene.get("scene_id", "")
        scene_type = scene.get("scene_type", "statement")

        try:
            # 使用 LLM 设计布局
            design = await self._design_with_llm(
                scene_id, scene_type, intents, canvas, visual_strategy
            )

            # 转换为 SceneLayoutSpec
            layout_spec = self._convert_to_layout_spec(scene_id, design, canvas)
            return layout_spec

        except Exception as e:
            from utils.logger import get_logger
            logger = get_logger(__name__)
            logger.warning(
                "LLM layout design failed for scene %s, falling back to template solver: %s",
                scene_id,
                str(e)
            )

            if self.fallback_to_solver:
                # 回退到基于模板的布局求解
                from layout.solver import LayoutSolver
                solver = LayoutSolver()
                return solver.solve(intents, canvas, scene_type)
            else:
                raise

    async def _design_with_llm(
        self,
        scene_id: str,
        scene_type: str,
        intents: list[Any],
        canvas: CanvasSpec,
        visual_strategy: dict[str, Any] | None,
    ) -> LayoutDesignResult:
        """使用 LLM 设计布局"""

        # 提取意图信息
        intent_descriptions = []
        for intent in intents:
            desc = f"- {intent.role}: {intent.text[:50]}... (重要性: {intent.importance}, 组件: {intent.primitive_type})"
            intent_descriptions.append(desc)
        intents_text = "\n".join(intent_descriptions)

        style_context = ""
        if visual_strategy:
            style_family = visual_strategy.get("style_family", "minimal_light")
            theme = visual_strategy.get("theme_profile", {})
            style_context = f"""
视觉风格：{style_family}
主色调：{theme.get('primary_accent', '#38B2AC')}
辅助色：{theme.get('secondary_accent', '#F6AD55')}
"""

        prompt = f"""你是一个专业的视觉设计师。请为以下场景设计布局。

场景类型：{scene_type}
场景 ID：{scene_id}

画布规格：
- 宽度：{canvas.width}px
- 高度：{canvas.height}px
- 安全区域：上 {canvas.safe_top}px, 右 {canvas.safe_right}px, 下 {canvas.safe_bottom}px, 左 {canvas.safe_left}px
- 可用宽度：{canvas.width - canvas.safe_left - canvas.safe_right}px
- 可用高度：{canvas.height - canvas.safe_top - canvas.safe_bottom}px

需要布局的元素：
{intents_text}
{style_context}

**重要：你必须返回一个包含以下所有字段的 JSON 对象：**

{{
  "elements": [
    {{
      "element_id": "元素唯一标识（如 {scene_id}_title）",
      "element_type": "元素类型（title, body, stat, quote, image, icon, decoration）",
      "primitive_type": "视觉组件类型（与意图中的 primitive_type 对应）",
      "position_x": 元素左上角 X 坐标（数字，单位 px）,
      "position_y": 元素左上角 Y 坐标（数字，单位 px）,
      "width": 元素宽度（数字，单位 px）,
      "height": 元素高度（数字，单位 px）,
      "z_index": 层级（0-100，数字越大越在上层）,
      "reveal_order": 出场顺序（0-10，0 最先出现）,
      "text_content": "文本内容（如果有）",
      "style_notes": "样式说明（如'大标题，粗体，居中对齐'）",
      "animation_notes": "动画说明（如'从下方滑入，持续 0.5s'）"
    }}
  ],
  "composition": "构图方式（centered/asymmetric/grid/split/layered）",
  "visual_hierarchy": ["按重要性排列的元素 ID 列表"],
  "focal_point": "最重要的元素 ID",
  "design_reasoning": "设计理由（2-3 句话）",
  "estimated_density": "布局密度（sparse/medium/dense）"
}}

设计要求：
- 所有元素必须在安全区域内（考虑 safe_top, safe_right, safe_bottom, safe_left）
- 元素之间要有合理的间距，避免重叠（除非有意为之）
- 重要元素（importance 高）应该更大、更突出
- 考虑视觉流动：观众的视线应该自然地从一个元素移动到下一个
- 标题通常在上方，正文在中间，数据或强调内容可以在任何位置
- 如果是对比场景（contrast），考虑左右分屏
- 如果是数据场景（data_point），突出数字
- 动画出场顺序要合理：通常先标题，再内容，最后装饰
- 考虑视觉风格的特点（如 minimal_light 要留白多，product_ui 可以更紧凑）

示例元素尺寸参考：
- HeroTitle: 宽 600-900px, 高 80-150px
- BodyCard: 宽 500-800px, 高 150-400px
- StatPanel: 宽 400-600px, 高 200-300px
- QuoteCard: 宽 600-900px, 高 200-400px
"""

        messages = [{"role": "user", "content": prompt}]

        result = await ainvoke_structured(
            model=self.model,
            schema=LayoutDesignResult,
            messages=messages,
            operation=f"layout_design:{scene_id}",
        )

        return result

    def _convert_to_layout_spec(
        self,
        scene_id: str,
        design: LayoutDesignResult,
        canvas: CanvasSpec,
    ) -> SceneLayoutSpec:
        """将 LLM 设计结果转换为 SceneLayoutSpec"""

        elements: list[LayoutElement] = []

        # element_type -> LayoutElement.role 映射
        _ROLE_MAP = {
            "title": "hero",
            "body": "body",
            "stat": "stat",
            "quote": "quote",
            "image": "image",
            "icon": "icon",
            "decoration": "decoration",
            "cta": "cta",
        }

        for elem_spec in design.elements:
            role = _ROLE_MAP.get(elem_spec.element_type, elem_spec.element_type)
            element = LayoutElement(
                id=elem_spec.element_id,
                primitive_type=elem_spec.primitive_type,
                role=role,
                box={
                    "x": elem_spec.position_x,
                    "y": elem_spec.position_y,
                    "width": elem_spec.width,
                    "height": elem_spec.height,
                    "z_index": elem_spec.z_index,
                },
                reveal_order=elem_spec.reveal_order,
                style={
                    "notes": elem_spec.style_notes,
                    "animation_notes": elem_spec.animation_notes,
                },
                content={"text": elem_spec.text_content} if elem_spec.text_content else {},
            )
            elements.append(element)

        return SceneLayoutSpec(
            scene_id=scene_id,
            canvas=canvas,
            elements=elements,
            metadata={
                "composition": design.composition,
                "visual_hierarchy": design.visual_hierarchy,
                "focal_point": design.focal_point,
                "design_reasoning": design.design_reasoning,
                "estimated_density": design.estimated_density,
                "generated_by": "llm_layout_designer",
            },
        )
