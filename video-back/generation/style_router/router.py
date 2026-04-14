from __future__ import annotations

from typing import Any

from generation.style_router.profiles import (
    AssetPolicy,
    MotionProfile,
    SceneVisualPolicy,
    ThemeProfile,
    VisualStrategy,
    get_theme_profile,
)
from layout.primitives import get_primitives_for_scene_type


class StyleRouter:
    def route(
        self,
        storyboard: dict[str, Any],
        user_preference: dict[str, Any] | None = None,
    ) -> VisualStrategy:
        style_family = self._determine_style_family(storyboard, user_preference)
        theme_profile = self._select_theme(style_family, user_preference)
        motion_profile = self._select_motion_profile(style_family)
        asset_policy = self._select_asset_policy(style_family)
        scene_type_mapping = self._build_scene_type_mapping(storyboard)

        return VisualStrategy(
            style_family=style_family,
            theme_profile=theme_profile,
            motion_profile=motion_profile,
            asset_policy=asset_policy,
            scene_type_mapping=scene_type_mapping,
        )

    def _determine_style_family(
        self,
        storyboard: dict[str, Any],
        user_preference: dict[str, Any] | None,
    ) -> str:
        if user_preference and user_preference.get("style_family"):
            return user_preference["style_family"]

        scenes = storyboard.get("scenes", [])
        if not scenes:
            return "minimal_light"

        scene_types = [scene.get("scene_type", "statement") for scene in scenes]

        data_heavy_types = {"data_point", "chart", "metrics"}
        product_types = {"product_demo", "screenshot"}
        editorial_types = {"quote", "emotion_peak"}

        data_count = sum(1 for st in scene_types if st in data_heavy_types)
        product_count = sum(1 for st in scene_types if st in product_types)
        editorial_count = sum(1 for st in scene_types if st in editorial_types)

        if data_count > len(scenes) * 0.4:
            return "diagrammatic_minimal"
        elif product_count > len(scenes) * 0.3:
            return "product_ui"
        elif editorial_count > len(scenes) * 0.3:
            return "editorial_typography"
        else:
            return "minimal_light"

    def _select_theme(
        self,
        style_family: str,
        user_preference: dict[str, Any] | None,
    ) -> ThemeProfile:
        theme_mapping = {
            "minimal_light": "minimal_light",
            "diagrammatic_minimal": "diagrammatic_minimal",
            "product_ui": "product_ui",
            "editorial_typography": "editorial_typography",
        }
        theme_id = theme_mapping.get(style_family, "minimal_light")
        return get_theme_profile(theme_id)

    def _select_motion_profile(self, style_family: str) -> MotionProfile:
        if style_family == "product_ui":
            return MotionProfile(
                transition_duration=0.6,
                easing="ease-out",
                reveal_style="slide",
                emphasis_style="bounce",
            )
        elif style_family == "editorial_typography":
            return MotionProfile(
                transition_duration=0.8,
                easing="ease-in-out",
                reveal_style="fade",
                emphasis_style="subtle",
            )
        else:
            return MotionProfile(
                transition_duration=0.5,
                easing="ease-in-out",
                reveal_style="fade",
                emphasis_style="scale",
            )

    def _select_asset_policy(self, style_family: str) -> AssetPolicy:
        if style_family == "product_ui":
            return AssetPolicy(
                allow_external_images=True,
                allow_icons=True,
                icon_style="filled",
                image_treatment="rounded",
            )
        elif style_family == "editorial_typography":
            return AssetPolicy(
                allow_external_images=True,
                allow_icons=False,
                icon_style="none",
                image_treatment="natural",
            )
        else:
            return AssetPolicy(
                allow_external_images=True,
                allow_icons=True,
                icon_style="outline",
                image_treatment="natural",
            )

    def _build_scene_type_mapping(
        self,
        storyboard: dict[str, Any],
    ) -> dict[str, SceneVisualPolicy]:
        mapping: dict[str, SceneVisualPolicy] = {}
        scenes = storyboard.get("scenes", [])

        for scene in scenes:
            scene_type = scene.get("scene_type", "statement")
            if scene_type not in mapping:
                mapping[scene_type] = SceneVisualPolicy(
                    scene_type=scene_type,
                    allowed_primitives=get_primitives_for_scene_type(scene_type),
                    preferred_composition="centered",
                    max_density="medium",
                )

        return mapping
