from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from generation.style_router.profiles import VisualStrategy
from models.get_model import get_model
from utils.structured_output import ainvoke_structured


class StyleRecommendation(BaseModel):
    """LLM 推荐的风格"""
    style_family: str = Field(description="推荐的风格家族：minimal_light, diagrammatic_minimal, product_ui, editorial_typography")
    confidence: float = Field(description="推荐置信度 0-1", ge=0, le=1)
    reasoning: str = Field(description="推荐理由")
    target_audience: str = Field(description="目标受众：professional, general, youth, executive")
    content_emotion: str = Field(description="内容情感：serious, casual, inspiring, urgent, educational")
    information_density: str = Field(description="信息密度：data_heavy, narrative, product_focused, balanced")
    brand_tone: str = Field(description="品牌调性：tech, humanistic, business, creative, academic")
    color_suggestions: list[str] = Field(description="配色建议（hex 格式）")
    motion_suggestions: str = Field(description="动效建议")


class StyleAnalyzer:
    """LLM 驱动的风格分析器

    分析脚本内容，理解情感、受众、目的，智能推荐最合适的视觉风格。
    替代原有的基于场景类型统计的硬编码规则。
    """

    def __init__(self, fallback_to_rules: bool = True):
        """
        Args:
            fallback_to_rules: 如果 LLM 调用失败，是否回退到基于规则的选择
        """
        self.model = get_model("visual_architect")
        self.fallback_to_rules = fallback_to_rules

    async def analyze(
        self,
        script: str,
        storyboard: dict[str, Any],
        user_preference: dict[str, Any] | None = None,
    ) -> StyleRecommendation:
        """分析脚本并推荐风格

        Args:
            script: 完整脚本
            storyboard: 分镜脚本（包含 scenes 列表）
            user_preference: 用户偏好设置

        Returns:
            StyleRecommendation
        """
        try:
            # 使用 LLM 分析风格
            recommendation = await self._analyze_with_llm(script, storyboard, user_preference)
            return recommendation

        except Exception as e:
            if self.fallback_to_rules:
                # 回退到基于规则的风格选择
                from generation.style_router.router import StyleRouter
                router = StyleRouter()
                visual_strategy = router.route(storyboard, user_preference)

                # 转换为 StyleRecommendation 格式
                return StyleRecommendation(
                    style_family=visual_strategy.style_family,
                    confidence=0.7,
                    reasoning="基于规则的风格选择（LLM 调用失败）",
                    target_audience="general",
                    content_emotion="neutral",
                    information_density="balanced",
                    brand_tone="business",
                    color_suggestions=[],
                    motion_suggestions="标准动效",
                )
            else:
                raise

    async def _analyze_with_llm(
        self,
        script: str,
        storyboard: dict[str, Any],
        user_preference: dict[str, Any] | None,
    ) -> StyleRecommendation:
        """使用 LLM 分析风格"""

        scenes = storyboard.get("scenes", [])
        scene_count = len(scenes)

        # 提取场景类型统计
        scene_types = [scene.get("scene_type", "statement") for scene in scenes]
        scene_type_summary = ", ".join(set(scene_types))

        preference_context = ""
        if user_preference:
            if user_preference.get("style_family"):
                preference_context += f"\n用户指定风格：{user_preference['style_family']}"
            if user_preference.get("brand_colors"):
                preference_context += f"\n品牌色：{', '.join(user_preference['brand_colors'])}"

        # 截取脚本前 800 字符
        script_preview = script[:800] + ("..." if len(script) > 800 else "")

        prompt = f"""你是一个视频风格设计专家。请分析以下视频脚本，推荐最合适的视觉风格。

脚本内容：
{script_preview}

场景信息：
- 场景数量：{scene_count}
- 场景类型：{scene_type_summary}
{preference_context}

可选的风格家族：
1. **minimal_light**（简约明亮）
   - 特点：干净的白色背景，柔和的色彩，现代感强
   - 适用：通用内容，品牌宣传，产品介绍
   - 受众：大众、专业人士

2. **diagrammatic_minimal**（图表化极简）
   - 特点：清晰的对比色，适合数据展示，专业感强
   - 适用：数据报告，分析内容，技术说明
   - 受众：专业人士，决策者

3. **product_ui**（产品界面）
   - 特点：科技感，渐变和阴影，现代 UI 设计
   - 适用：软件产品，App 演示，科技创新
   - 受众：科技爱好者，产品用户

4. **editorial_typography**（编辑排版）
   - 特点：强调文字，优雅的字体，人文气息
   - 适用：故事叙述，品牌故事，文化内容
   - 受众：文化人群，高端用户

请完成以下分析：

1. **推荐风格家族**：从上述 4 个风格中选择最合适的一个

2. **推荐置信度**：0-1 之间，表示推荐的确定程度
   - 0.9-1.0: 非常确定
   - 0.7-0.9: 比较确定
   - 0.5-0.7: 一般确定
   - < 0.5: 不太确定

3. **推荐理由**：简要说明为什么选择这个风格（2-3 句话）

4. **目标受众**：professional（专业人士）, general（大众）, youth（年轻人）, executive（高管）

5. **内容情感**：serious（严肃）, casual（轻松）, inspiring（激励）, urgent（紧迫）, educational（教育）

6. **信息密度**：
   - data_heavy: 数据密集型（大量图表、统计）
   - narrative: 叙事型（故事、案例）
   - product_focused: 产品聚焦型（产品演示）
   - balanced: 平衡型（混合内容）

7. **品牌调性**：tech（科技）, humanistic（人文）, business（商务）, creative（创意）, academic（学术）

8. **配色建议**：推荐 2-3 个主色调（hex 格式）

9. **动效建议**：简要描述适合的动画风格（如"快速流畅"、"优雅缓慢"、"弹性有趣"）

分析要点：
- 仔细阅读脚本，理解内容主题和情感基调
- 考虑场景类型分布（如数据场景多则倾向 diagrammatic_minimal）
- 考虑目标受众和使用场景
- 如果用户指定了风格，优先考虑但要评估是否合适
- 给出明确的推荐和充分的理由
"""

        messages = [{"role": "user", "content": prompt}]

        result = await ainvoke_structured(
            model=self.model,
            schema=StyleRecommendation,
            messages=messages,
            operation="style_analysis",
        )

        return result

    def should_use_llm_recommendation(
        self,
        llm_recommendation: StyleRecommendation,
        rule_based_style: str,
    ) -> bool:
        """判断是否应该使用 LLM 推荐的风格

        Args:
            llm_recommendation: LLM 推荐结果
            rule_based_style: 基于规则的风格选择

        Returns:
            True 表示使用 LLM 推荐，False 表示使用规则推荐
        """
        # 如果 LLM 置信度很高（>= 0.8），使用 LLM 推荐
        if llm_recommendation.confidence >= 0.8:
            return True

        # 如果 LLM 和规则推荐一致，使用 LLM 推荐（因为有更详细的理由）
        if llm_recommendation.style_family == rule_based_style:
            return True

        # 如果 LLM 置信度中等（0.6-0.8），且规则推荐是默认值，使用 LLM 推荐
        if llm_recommendation.confidence >= 0.6 and rule_based_style == "minimal_light":
            return True

        # 其他情况使用规则推荐（更保守）
        return False
