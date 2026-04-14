from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from generation.style_router.profiles import ThemeProfile
from models.get_model import get_model
from utils.structured_output import ainvoke_structured


class ColorPalette(BaseModel):
    """LLM 生成的配色方案"""
    background: str = Field(description="背景色 (hex)")
    primary_accent: str = Field(description="主色调 (hex)")
    secondary_accent: str = Field(description="辅助色 (hex)")
    text_main: str = Field(description="主文字色 (hex)")
    text_muted: str = Field(description="次要文字色 (hex)")
    highlight: str = Field(description="高亮色 (hex)")
    stroke: str = Field(description="描边色 (hex)")
    reasoning: str = Field(description="配色理由")
    contrast_ratio: float = Field(description="对比度评分 1-10", ge=1, le=10)


class ThemeGenerationResult(BaseModel):
    """主题生成结果"""
    palette: ColorPalette
    font_family_primary: str = Field(description="主字体")
    font_family_secondary: str = Field(description="辅助字体")
    base_font_size: int = Field(description="基础字号", ge=12, le=72)
    spacing_unit: int = Field(description="间距单位 px", ge=4, le=32)
    border_radius: int = Field(description="圆角半径 px", ge=0, le=48)
    mood: str = Field(description="整体氛围：modern, classic, playful, serious, elegant")


class ThemeGenerator:
    """LLM 驱动的主题配色生成器

    根据脚本内容、风格家族和品牌色，使用 LLM 生成定制化的主题配色方案。
    """

    def __init__(self, fallback_to_preset: bool = True):
        """
        Args:
            fallback_to_preset: 如果 LLM 调用失败，是否回退到预设主题
        """
        self.model = get_model("visual_architect")
        self.fallback_to_preset = fallback_to_preset

    async def generate(
        self,
        style_family: str,
        script: str,
        brand_colors: list[str] | None = None,
        user_preference: dict[str, Any] | None = None,
    ) -> ThemeProfile:
        """生成主题配色

        Args:
            style_family: 风格家族 (minimal_light, diagrammatic_minimal, product_ui, editorial_typography)
            script: 视频脚本（用于理解内容情感）
            brand_colors: 品牌色列表（hex 格式）
            user_preference: 用户偏好设置

        Returns:
            ThemeProfile
        """
        try:
            # 使用 LLM 生成主题
            theme_result = await self._generate_with_llm(
                style_family, script, brand_colors, user_preference
            )

            # 转换为 ThemeProfile
            theme_profile = self._convert_to_theme_profile(theme_result)
            return theme_profile

        except Exception as e:
            if self.fallback_to_preset:
                # 回退到预设主题
                from generation.style_router.profiles import get_theme_profile
                return get_theme_profile(style_family)
            else:
                raise

    async def _generate_with_llm(
        self,
        style_family: str,
        script: str,
        brand_colors: list[str] | None,
        user_preference: dict[str, Any] | None,
    ) -> ThemeGenerationResult:
        """使用 LLM 生成主题"""

        # 风格家族描述
        style_descriptions = {
            "minimal_light": "简约明亮风格，干净的白色背景，柔和的色彩，现代感强",
            "diagrammatic_minimal": "图表化极简风格，适合数据展示，清晰的对比色，专业感",
            "product_ui": "产品界面风格，科技感，渐变和阴影，现代 UI 设计",
            "editorial_typography": "编辑排版风格，强调文字，优雅的字体，人文气息",
        }

        style_desc = style_descriptions.get(style_family, "简约现代风格")

        brand_context = ""
        if brand_colors:
            brand_context = f"\n品牌色要求：{', '.join(brand_colors)}（必须在配色方案中使用）"

        preference_context = ""
        if user_preference:
            if user_preference.get("prefer_dark_mode"):
                preference_context += "\n用户偏好：深色模式"
            if user_preference.get("high_contrast"):
                preference_context += "\n用户偏好：高对比度"

        # 截取脚本前 500 字符用于分析
        script_preview = script[:500] + ("..." if len(script) > 500 else "")

        prompt = f"""你是一个专业的视觉设计师。请为以下视频生成配色方案。

风格家族：{style_family}
风格描述：{style_desc}

脚本内容：
{script_preview}
{brand_context}
{preference_context}

请生成一套完整的配色方案，包括：

1. **配色方案**（所有颜色使用 hex 格式，如 #FFFFFF）：
   - background: 背景色
   - primary_accent: 主色调（用于按钮、重点元素）
   - secondary_accent: 辅助色（用于次要元素、装饰）
   - text_main: 主文字色
   - text_muted: 次要文字色（用于说明文字）
   - highlight: 高亮色（用于强调、悬停状态）
   - stroke: 描边色（用于边框、分割线）

2. **字体选择**：
   - font_family_primary: 主字体（标题用，如 "Inter", "Roboto", "Noto Sans SC"）
   - font_family_secondary: 辅助字体（正文用）
   - base_font_size: 基础字号（px，通常 16-24）

3. **设计参数**：
   - spacing_unit: 间距单位（px，通常 8 或 16）
   - border_radius: 圆角半径（px，0 表示直角，8-24 表示圆角）
   - mood: 整体氛围（modern, classic, playful, serious, elegant）

4. **配色理由**：简要说明为什么选择这套配色

5. **对比度评分**：评估文字与背景的对比度（1-10 分，7 分以上符合 WCAG AA 标准）

设计要求：
- 配色必须符合 WCAG AA 对比度标准（text_main 与 background 对比度 ≥ 4.5:1）
- 如果提供了品牌色，必须将其作为 primary_accent 或 secondary_accent
- 配色要与脚本的情感基调匹配（如科技类用蓝色系，自然类用绿色系）
- 整体配色要和谐统一，避免过于花哨
- 考虑风格家族的特点（如 minimal_light 要明亮简洁，editorial_typography 要优雅克制）
"""

        messages = [{"role": "user", "content": prompt}]

        result = await ainvoke_structured(
            model=self.model,
            schema=ThemeGenerationResult,
            messages=messages,
            operation=f"theme_generation:{style_family}",
        )

        return result

    def _convert_to_theme_profile(self, result: ThemeGenerationResult) -> ThemeProfile:
        """将 LLM 生成结果转换为 ThemeProfile"""

        return ThemeProfile(
            background=result.palette.background,
            primary_accent=result.palette.primary_accent,
            secondary_accent=result.palette.secondary_accent,
            text_main=result.palette.text_main,
            text_muted=result.palette.text_muted,
            highlight=result.palette.highlight,
            stroke=result.palette.stroke,
            font_family_primary=result.font_family_primary,
            font_family_secondary=result.font_family_secondary,
            base_font_size=result.base_font_size,
            spacing_unit=result.spacing_unit,
            border_radius=result.border_radius,
        )
