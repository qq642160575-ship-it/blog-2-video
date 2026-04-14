from __future__ import annotations

from pathlib import Path

from rendering.schemas import ValidationIssue, VisualValidationReport
from utils.logger import get_logger

logger = get_logger(__name__)


class VisualValidator:
    """
    视觉验证器

    验证渲染结果是否符合预期:
    - 图片是否存在
    - 图片尺寸是否正确
    - (未来) OCR 检查文字是否被裁切
    - (未来) 视觉模型评估可读性
    """

    def __init__(self, enable_ocr: bool = False, enable_visual_model: bool = False) -> None:
        self.enable_ocr = enable_ocr
        self.enable_visual_model = enable_visual_model

    async def validate(
        self,
        scene_id: str,
        preview_image_url: str,
        expected_width: int = 1080,
        expected_height: int = 1920,
    ) -> VisualValidationReport:
        """
        验证预览图

        Args:
            scene_id: 场景 ID
            preview_image_url: 预览图路径
            expected_width: 期望宽度
            expected_height: 期望高度

        Returns:
            VisualValidationReport: 验证报告
        """
        issues: list[ValidationIssue] = []

        # 检查文件是否存在
        image_path = Path(preview_image_url)
        if not image_path.exists():
            issues.append(
                ValidationIssue(
                    code="IMAGE_NOT_FOUND",
                    severity="error",
                    message=f"预览图不存在: {preview_image_url}",
                    detail={"path": preview_image_url},
                )
            )
            return VisualValidationReport(
                scene_id=scene_id,
                passed=False,
                issues=issues,
            )

        # 检查文件大小
        file_size = image_path.stat().st_size
        if file_size == 0:
            issues.append(
                ValidationIssue(
                    code="IMAGE_EMPTY",
                    severity="error",
                    message="预览图文件为空",
                    detail={"path": preview_image_url},
                )
            )

        # TODO: 使用 PIL 检查图片尺寸
        # try:
        #     from PIL import Image
        #     img = Image.open(image_path)
        #     if img.width != expected_width or img.height != expected_height:
        #         issues.append(ValidationIssue(
        #             code="IMAGE_SIZE_MISMATCH",
        #             severity="warning",
        #             message=f"图片尺寸不匹配: 期望 {expected_width}x{expected_height}, 实际 {img.width}x{img.height}",
        #             detail={"expected": [expected_width, expected_height], "actual": [img.width, img.height]}
        #         ))
        # except Exception as e:
        #     issues.append(ValidationIssue(
        #         code="IMAGE_LOAD_FAILED",
        #         severity="error",
        #         message=f"无法加载图片: {str(e)}",
        #         detail={"error": str(e)}
        #     ))

        # TODO: OCR 检查文字是否被裁切
        if self.enable_ocr:
            ocr_issues = await self._validate_with_ocr(scene_id, image_path)
            issues.extend(ocr_issues)

        # TODO: 视觉模型评估
        if self.enable_visual_model:
            visual_issues = await self._validate_with_visual_model(scene_id, image_path)
            issues.extend(visual_issues)

        passed = not any(issue.severity == "error" for issue in issues)

        return VisualValidationReport(
            scene_id=scene_id,
            passed=passed,
            issues=issues,
            metadata={
                "file_size": file_size,
                "ocr_enabled": self.enable_ocr,
                "visual_model_enabled": self.enable_visual_model,
            },
        )

    async def _validate_with_ocr(
        self,
        scene_id: str,
        image_path: Path,
    ) -> list[ValidationIssue]:
        """
        使用 OCR 验证文字是否被裁切

        TODO: 实现 OCR 验证
        - 使用 pytesseract 或 EasyOCR
        - 检测文字边界
        - 判断是否超出画布
        """
        logger.debug(f"OCR validation for {scene_id} (not implemented)")
        return []

    async def _validate_with_visual_model(
        self,
        scene_id: str,
        image_path: Path,
    ) -> list[ValidationIssue]:
        """
        使用视觉模型评估可读性

        TODO: 实现视觉模型验证
        - 使用 Claude Vision 或其他视觉模型
        - 评估文字可读性
        - 检查布局是否过度拥挤或空洞
        - 检查是否偏离主题风格
        """
        logger.debug(f"Visual model validation for {scene_id} (not implemented)")
        return []


class StrictVisualValidator(VisualValidator):
    """
    严格的视觉验证器

    启用所有验证功能,用于生产环境
    """

    def __init__(self) -> None:
        super().__init__(enable_ocr=True, enable_visual_model=True)
