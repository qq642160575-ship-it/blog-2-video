"""LLM 增强配置

控制 LLM 在视频生成流程中的参与程度。
"""

from typing import Literal


class LLMEnhancementConfig:
    """LLM 增强配置"""

    def __init__(
        self,
        mode: Literal["disabled", "hybrid", "full"] = "hybrid",
        confidence_threshold: float = 0.7,
        enable_style_analysis: bool = True,
        enable_theme_generation: bool = True,
        enable_semantic_extraction: bool = True,
        enable_layout_design: bool = True,
    ):
        """
        Args:
            mode: 运行模式
                - "disabled": 完全禁用 LLM 增强，使用纯规则
                - "hybrid": 混合模式，LLM 和规则共存，根据置信度选择（推荐）
                - "full": 完全使用 LLM，规则仅作为 fallback
            confidence_threshold: LLM 推荐的置信度阈值（0-1）
                - 高于此值采用 LLM 推荐
                - 低于此值回退到规则
                - 推荐值：0.7
            enable_style_analysis: 是否启用 LLM 风格分析
            enable_theme_generation: 是否启用 LLM 主题生成
            enable_semantic_extraction: 是否启用 LLM 语义提取
            enable_layout_design: 是否启用 LLM 布局设计
        """
        self.mode = mode
        self.confidence_threshold = confidence_threshold
        self.enable_style_analysis = enable_style_analysis
        self.enable_theme_generation = enable_theme_generation
        self.enable_semantic_extraction = enable_semantic_extraction
        self.enable_layout_design = enable_layout_design

    @property
    def is_enabled(self) -> bool:
        """是否启用 LLM 增强"""
        return self.mode != "disabled"

    @property
    def is_full_mode(self) -> bool:
        """是否为完全 LLM 模式"""
        return self.mode == "full"

    @property
    def is_hybrid_mode(self) -> bool:
        """是否为混合模式"""
        return self.mode == "hybrid"

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "mode": self.mode,
            "confidence_threshold": self.confidence_threshold,
            "enable_style_analysis": self.enable_style_analysis,
            "enable_theme_generation": self.enable_theme_generation,
            "enable_semantic_extraction": self.enable_semantic_extraction,
            "enable_layout_design": self.enable_layout_design,
        }


# 预设配置

# 保守模式：仅在高置信度时使用 LLM
CONSERVATIVE_CONFIG = LLMEnhancementConfig(
    mode="hybrid",
    confidence_threshold=0.85,
    enable_style_analysis=True,
    enable_theme_generation=False,  # 主题使用预设
    enable_semantic_extraction=True,
    enable_layout_design=False,  # 布局使用模板
)

# 平衡模式：LLM 和规则平衡（推荐）
BALANCED_CONFIG = LLMEnhancementConfig(
    mode="hybrid",
    confidence_threshold=0.7,
    enable_style_analysis=True,
    enable_theme_generation=True,
    enable_semantic_extraction=True,
    enable_layout_design=True,
)

# 激进模式：最大化 LLM 使用
AGGRESSIVE_CONFIG = LLMEnhancementConfig(
    mode="full",
    confidence_threshold=0.5,
    enable_style_analysis=True,
    enable_theme_generation=True,
    enable_semantic_extraction=True,
    enable_layout_design=True,
)

# 禁用模式：纯规则
DISABLED_CONFIG = LLMEnhancementConfig(
    mode="disabled",
    confidence_threshold=1.0,
    enable_style_analysis=False,
    enable_theme_generation=False,
    enable_semantic_extraction=False,
    enable_layout_design=False,
)

# 默认配置
DEFAULT_CONFIG = BALANCED_CONFIG
