from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from layout.primitives import PrimitiveIntent
from models.get_model import get_model
from utils.structured_output import ainvoke_structured


class ExtractedElement(BaseModel):
    """LLM 提取的视觉元素"""
    element_type: str = Field(description="元素类型：title, subtitle, body, stat, quote, cta, comparison_left, comparison_right")
    text: str = Field(description="元素文本内容")
    importance: int = Field(description="重要性 1-100", ge=1, le=100)
    primitive_type: str = Field(description="推荐的视觉组件：HeroTitle, BodyCard, StatPanel, QuoteCard 等")
    preferred_region: str = Field(description="推荐位置：top, middle, bottom, left, right, center")
    reasoning: str = Field(description="选择理由")


class SemanticAnalysisResult(BaseModel):
    """语义分析结果"""
    elements: list[ExtractedElement] = Field(description="提取的视觉元素列表")
    visual_hierarchy: list[str] = Field(description="视觉层级顺序（element_type 列表）")
    key_message: str = Field(description="场景核心信息（一句话总结）")
    emotional_tone: str = Field(description="情感基调：neutral, positive, urgent, professional, casual")


class SemanticIntentExtractor:
    """LLM 增强的语义意图提取器

    替代原有的基于规则的 SceneIntentGenerator，使用 LLM 理解场景语义，
    智能提取关键信息并生成视觉意图。
    """

    def __init__(self, fallback_to_rules: bool = True):
        """
        Args:
            fallback_to_rules: 如果 LLM 调用失败，是否回退到基于规则的提取
        """
        self.model = get_model("visual_architect")
        self.fallback_to_rules = fallback_to_rules

    async def extract(
        self,
        scene: dict[str, Any],
        visual_strategy: dict[str, Any] | None = None,
    ) -> list[PrimitiveIntent]:
        """提取场景的视觉意图

        Args:
            scene: 场景数据，包含 scene_id, scene_type, script
            visual_strategy: 视觉策略（可选）

        Returns:
            PrimitiveIntent 列表
        """
        scene_id = scene.get("scene_id", "")
        scene_type = scene.get("scene_type", "statement")
        script_text = scene.get("script", "")

        if not script_text.strip():
            return []

        try:
            # 使用 LLM 进行语义分析
            analysis = await self._analyze_with_llm(scene_id, scene_type, script_text, visual_strategy)

            # 转换为 PrimitiveIntent
            intents = self._convert_to_intents(scene_id, analysis)
            return intents

        except Exception as e:
            if self.fallback_to_rules:
                # 回退到基于规则的提取
                from generation.scene_intent.generator import SceneIntentGenerator
                fallback_generator = SceneIntentGenerator()
                return fallback_generator.generate(scene, visual_strategy or {})
            else:
                raise

    async def _analyze_with_llm(
        self,
        scene_id: str,
        scene_type: str,
        script_text: str,
        visual_strategy: dict[str, Any] | None,
    ) -> SemanticAnalysisResult:
        """使用 LLM 分析场景语义"""

        style_context = ""
        if visual_strategy:
            style_family = visual_strategy.get("style_family", "minimal_light")
            style_context = f"\n视觉风格：{style_family}"

        prompt = f"""你是一个视频场景分析专家。请分析以下场景脚本，提取需要可视化的关键信息。

场景类型：{scene_type}
场景脚本：
{script_text}
{style_context}

请完成以下任务：

1. **提取视觉元素**：识别脚本中需要可视化的信息，包括：
   - 主标题（最重要的一句话，简洁有力）
   - 副标题或解释文字（补充说明）
   - 数据点（数字、百分比、统计数据）
   - 引用或强调文字（需要特别突出的内容）
   - 对比内容（如果是对比场景，提取左右两侧内容）
   - 行动号召（CTA，如"立即购买"、"了解更多"）

2. **为每个元素标注**：
   - element_type: 元素类型（title, subtitle, body, stat, quote, cta, comparison_left, comparison_right）
   - text: 提取的文本内容（保持简洁，必要时改写）
   - importance: 重要性 1-100（主标题通常 100，次要信息 60-80）
   - primitive_type: 推荐的视觉组件类型
     * HeroTitle: 大标题
     * BodyCard: 正文卡片
     * StatPanel: 数据面板
     * QuoteCard: 引用卡片
     * CalloutBox: 强调框
     * ComparisonCard: 对比卡片
   - preferred_region: 推荐位置（top, middle, bottom, left, right, center）
   - reasoning: 为什么这样选择（简短说明）

3. **确定视觉层级**：按照观看顺序排列元素类型

4. **总结核心信息**：用一句话概括场景要传达的核心信息

5. **判断情感基调**：neutral（中性）, positive（积极）, urgent（紧迫）, professional（专业）, casual（轻松）

注意事项：
- 提取的文本要简洁，去除冗余
- 数据要准确提取，保留单位
- 如果脚本很长，只提取最关键的 3-5 个元素
- 考虑场景类型的特点（如 data_point 场景要突出数据）
"""

        messages = [{"role": "user", "content": prompt}]

        result = await ainvoke_structured(
            model=self.model,
            schema=SemanticAnalysisResult,
            messages=messages,
            operation=f"semantic_intent_extract:{scene_id}",
        )

        return result

    def _convert_to_intents(
        self,
        scene_id: str,
        analysis: SemanticAnalysisResult,
    ) -> list[PrimitiveIntent]:
        """将 LLM 分析结果转换为 PrimitiveIntent"""

        intents: list[PrimitiveIntent] = []

        for idx, element in enumerate(analysis.elements):
            intent = PrimitiveIntent(
                id=f"{scene_id}_{element.element_type}_{idx}",
                role=element.element_type,
                primitive_type=element.primitive_type,
                importance=element.importance,
                text=element.text,
                preferred_region=element.preferred_region,
                metadata={
                    "reasoning": element.reasoning,
                    "emotional_tone": analysis.emotional_tone,
                    "key_message": analysis.key_message,
                },
            )
            intents.append(intent)

        return intents
