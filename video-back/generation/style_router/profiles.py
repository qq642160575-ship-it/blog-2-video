from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class ThemeProfile(BaseModel):
    theme_id: str
    name: str
    font_heading: str = "Inter"
    font_body: str = "Inter"
    color_background: str = "#FFFFFF"
    color_primary: str = "#000000"
    color_secondary: str = "#666666"
    color_text: str = "#000000"
    surface_style: str = "flat"
    corner_radius_scale: str = "medium"
    shadow_style: str = "subtle"
    stroke_style: str = "none"
    motion_style: str = "smooth"


class MotionProfile(BaseModel):
    transition_duration: float = 0.5
    easing: str = "ease-in-out"
    reveal_style: str = "fade"
    emphasis_style: str = "scale"


class AssetPolicy(BaseModel):
    allow_external_images: bool = True
    allow_icons: bool = True
    icon_style: str = "outline"
    image_treatment: str = "natural"


class SceneVisualPolicy(BaseModel):
    scene_type: str
    allowed_primitives: list[str]
    preferred_composition: str = "centered"
    max_density: str = "medium"
    asset_policy: dict[str, Any] = {}


class VisualStrategy(BaseModel):
    style_family: str
    theme_profile: ThemeProfile
    motion_profile: MotionProfile
    asset_policy: AssetPolicy
    scene_type_mapping: dict[str, SceneVisualPolicy] = {}


THEME_PROFILES: dict[str, ThemeProfile] = {
    "minimal_light": ThemeProfile(
        theme_id="minimal_light",
        name="简约明亮",
        font_heading="Inter",
        font_body="Inter",
        color_background="#FFFFFF",
        color_primary="#000000",
        color_secondary="#666666",
        color_text="#000000",
        surface_style="flat",
        corner_radius_scale="small",
        shadow_style="none",
        stroke_style="thin",
        motion_style="smooth",
    ),
    "diagrammatic_minimal": ThemeProfile(
        theme_id="diagrammatic_minimal",
        name="图表简约",
        font_heading="Inter",
        font_body="Inter",
        color_background="#F5F5F5",
        color_primary="#2563EB",
        color_secondary="#64748B",
        color_text="#1E293B",
        surface_style="card",
        corner_radius_scale="medium",
        shadow_style="subtle",
        stroke_style="medium",
        motion_style="smooth",
    ),
    "product_ui": ThemeProfile(
        theme_id="product_ui",
        name="产品界面",
        font_heading="Inter",
        font_body="Inter",
        color_background="#FAFAFA",
        color_primary="#6366F1",
        color_secondary="#94A3B8",
        color_text="#0F172A",
        surface_style="elevated",
        corner_radius_scale="large",
        shadow_style="prominent",
        stroke_style="none",
        motion_style="bouncy",
    ),
    "editorial_typography": ThemeProfile(
        theme_id="editorial_typography",
        name="编辑排版",
        font_heading="Playfair Display",
        font_body="Source Serif Pro",
        color_background="#FFFEF9",
        color_primary="#1A1A1A",
        color_secondary="#757575",
        color_text="#2D2D2D",
        surface_style="flat",
        corner_radius_scale="none",
        shadow_style="none",
        stroke_style="none",
        motion_style="elegant",
    ),
}


def get_theme_profile(theme_id: str) -> ThemeProfile:
    return THEME_PROFILES.get(theme_id, THEME_PROFILES["minimal_light"])
