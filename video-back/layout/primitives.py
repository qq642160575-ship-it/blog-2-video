from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class PrimitiveSpec(BaseModel):
    primitive_type: str
    min_width: int
    min_height: int
    max_text_lines: int | None = None
    min_font_size: int = 28
    default_padding: int = 24
    allow_rotation: bool = False
    can_overlap: bool = False
    allowed_roles: list[str]
    description: str = ""


PRIMITIVE_SPECS: dict[str, PrimitiveSpec] = {
    "HeroTitle": PrimitiveSpec(
        primitive_type="HeroTitle",
        min_width=600,
        min_height=120,
        max_text_lines=3,
        min_font_size=48,
        default_padding=32,
        allow_rotation=False,
        can_overlap=False,
        allowed_roles=["title", "heading", "hero"],
        description="强标题,大字号,优先上/中区域",
    ),
    "BodyCard": PrimitiveSpec(
        primitive_type="BodyCard",
        min_width=500,
        min_height=150,
        max_text_lines=5,
        min_font_size=28,
        default_padding=24,
        allow_rotation=False,
        can_overlap=False,
        allowed_roles=["body", "content", "description"],
        description="正文卡片,最多5行",
    ),
    "QuoteCard": PrimitiveSpec(
        primitive_type="QuoteCard",
        min_width=600,
        min_height=200,
        max_text_lines=4,
        min_font_size=32,
        default_padding=40,
        allow_rotation=False,
        can_overlap=False,
        allowed_roles=["quote", "citation"],
        description="引用卡片,需要较大留白",
    ),
    "StatPanel": PrimitiveSpec(
        primitive_type="StatPanel",
        min_width=300,
        min_height=200,
        max_text_lines=3,
        min_font_size=36,
        default_padding=24,
        allow_rotation=False,
        can_overlap=False,
        allowed_roles=["stat", "metric", "number"],
        description="单指标面板,数字优先",
    ),
    "MetricGrid": PrimitiveSpec(
        primitive_type="MetricGrid",
        min_width=700,
        min_height=300,
        max_text_lines=None,
        min_font_size=24,
        default_padding=20,
        allow_rotation=False,
        can_overlap=False,
        allowed_roles=["metrics", "grid", "data"],
        description="多指标网格布局",
    ),
    "StepTimeline": PrimitiveSpec(
        primitive_type="StepTimeline",
        min_width=600,
        min_height=400,
        max_text_lines=None,
        min_font_size=24,
        default_padding=20,
        allow_rotation=False,
        can_overlap=False,
        allowed_roles=["steps", "timeline", "process"],
        description="步骤流程时间线",
    ),
    "ComparisonSplit": PrimitiveSpec(
        primitive_type="ComparisonSplit",
        min_width=800,
        min_height=400,
        max_text_lines=None,
        min_font_size=28,
        default_padding=24,
        allow_rotation=False,
        can_overlap=False,
        allowed_roles=["comparison", "contrast", "split"],
        description="对比分屏布局",
    ),
    "ScreenshotFrame": PrimitiveSpec(
        primitive_type="ScreenshotFrame",
        min_width=600,
        min_height=400,
        max_text_lines=None,
        min_font_size=24,
        default_padding=16,
        allow_rotation=False,
        can_overlap=False,
        allowed_roles=["screenshot", "image", "demo"],
        description="截图框架,固定宽高比",
    ),
    "ChartCard": PrimitiveSpec(
        primitive_type="ChartCard",
        min_width=600,
        min_height=400,
        max_text_lines=2,
        min_font_size=24,
        default_padding=24,
        allow_rotation=False,
        can_overlap=False,
        allowed_roles=["chart", "graph", "visualization"],
        description="图表卡片,需要图表区域和标题区域",
    ),
    "TerminalSnippet": PrimitiveSpec(
        primitive_type="TerminalSnippet",
        min_width=600,
        min_height=150,
        max_text_lines=8,
        min_font_size=20,
        default_padding=16,
        allow_rotation=False,
        can_overlap=False,
        allowed_roles=["code", "terminal", "command"],
        description="代码/命令片段,等宽字体",
    ),
    "ImageStage": PrimitiveSpec(
        primitive_type="ImageStage",
        min_width=700,
        min_height=500,
        max_text_lines=None,
        min_font_size=24,
        default_padding=0,
        allow_rotation=False,
        can_overlap=False,
        allowed_roles=["image", "visual", "hero_image"],
        description="图片主体,优先大面积展示",
    ),
    "CalloutTag": PrimitiveSpec(
        primitive_type="CalloutTag",
        min_width=150,
        min_height=60,
        max_text_lines=2,
        min_font_size=20,
        default_padding=12,
        allow_rotation=True,
        can_overlap=True,
        allowed_roles=["callout", "tag", "label", "annotation"],
        description="辅助标注,不主导布局",
    ),
}


def get_primitive_spec(primitive_type: str) -> PrimitiveSpec | None:
    return PRIMITIVE_SPECS.get(primitive_type)


def get_primitives_for_scene_type(scene_type: str) -> list[str]:
    scene_type_mapping: dict[str, list[str]] = {
        "statement": ["HeroTitle", "BodyCard", "CalloutTag"],
        "contrast": ["ComparisonSplit", "HeroTitle", "CalloutTag"],
        "process": ["StepTimeline", "HeroTitle"],
        "timeline": ["StepTimeline", "BodyCard"],
        "data_point": ["StatPanel", "BodyCard", "CalloutTag"],
        "product_demo": ["ScreenshotFrame", "CalloutTag", "HeroTitle"],
        "quote": ["QuoteCard", "HeroTitle"],
        "emotion_peak": ["HeroTitle", "ImageStage"],
        "chart": ["ChartCard", "HeroTitle", "BodyCard"],
        "code": ["TerminalSnippet", "HeroTitle", "BodyCard"],
        "metrics": ["MetricGrid", "HeroTitle"],
    }
    return scene_type_mapping.get(scene_type, ["HeroTitle", "BodyCard"])


class PrimitiveIntent(BaseModel):
    id: str
    role: str
    primitive_type: str
    importance: int
    text: str | None = None
    preferred_region: str | None = None
    group_with: list[str] = []
    must_follow: list[str] = []
    metadata: dict[str, Any] = {}
