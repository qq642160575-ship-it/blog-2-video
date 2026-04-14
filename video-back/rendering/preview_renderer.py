from __future__ import annotations

import asyncio
import hashlib
import time
from pathlib import Path
from typing import Protocol

from rendering.schemas import RenderRequest, RenderResult
from utils.logger import get_logger

logger = get_logger(__name__)


class PreviewRenderer(Protocol):
    """预览渲染器接口"""

    async def render_scene_preview(
        self,
        scene_code: str,
        scene_id: str,
        frame: int = 0,
    ) -> RenderResult:
        """渲染场景预览"""
        ...


class MockPreviewRenderer:
    """
    Mock 预览渲染器

    用于开发和测试,不执行真实渲染,而是生成模拟的渲染结果。
    生产环境应该使用 RemotionPreviewRenderer 或其他真实渲染器。
    """

    def __init__(self, storage_root: str = ".cache/previews") -> None:
        self.storage_root = Path(storage_root)
        self.storage_root.mkdir(parents=True, exist_ok=True)

    async def render_scene_preview(
        self,
        scene_code: str,
        scene_id: str,
        frame: int = 0,
    ) -> RenderResult:
        """
        模拟渲染场景预览

        实际上不执行渲染,而是:
        1. 生成一个基于代码哈希的文件名
        2. 创建一个空的占位文件
        3. 返回渲染结果
        """
        start_time = time.time()

        logger.info(f"Mock rendering scene {scene_id} at frame {frame}")

        # 模拟渲染延迟
        await asyncio.sleep(0.1)

        # 生成文件名
        code_hash = hashlib.md5(scene_code.encode()).hexdigest()[:8]
        filename = f"{scene_id}_frame{frame}_{code_hash}.png"
        file_path = self.storage_root / filename

        # 创建占位文件
        file_path.write_text(f"Mock preview for {scene_id}")

        render_time_ms = (time.time() - start_time) * 1000

        return RenderResult(
            scene_id=scene_id,
            storage_url=str(file_path),
            width=1080,
            height=1920,
            frame=frame,
            metadata={
                "renderer": "mock",
                "code_hash": code_hash,
            },
            render_time_ms=render_time_ms,
        )


class RemotionPreviewRenderer:
    """
    Remotion 预览渲染器

    使用 Remotion CLI 或 Lambda 渲染真实的预览图。
    这是生产环境推荐的渲染器。

    TODO: 实现真实的 Remotion 渲染逻辑
    """

    def __init__(
        self,
        storage_root: str = ".cache/previews",
        remotion_root: str = "../video-front",
    ) -> None:
        self.storage_root = Path(storage_root)
        self.remotion_root = Path(remotion_root)
        self.storage_root.mkdir(parents=True, exist_ok=True)

    async def render_scene_preview(
        self,
        scene_code: str,
        scene_id: str,
        frame: int = 0,
    ) -> RenderResult:
        """
        使用 Remotion 渲染场景预览

        步骤:
        1. 将 scene_code 写入临时文件
        2. 调用 Remotion CLI 渲染
        3. 等待渲染完成
        4. 返回渲染结果

        TODO: 实现完整的 Remotion 集成
        """
        start_time = time.time()

        logger.info(f"Remotion rendering scene {scene_id} at frame {frame}")

        # TODO: 实现真实的 Remotion 渲染
        # 1. 写入代码到临时文件
        # 2. 调用 npx remotion still
        # 3. 等待渲染完成
        # 4. 移动文件到 storage_root

        # 暂时使用 mock 实现
        await asyncio.sleep(0.5)

        code_hash = hashlib.md5(scene_code.encode()).hexdigest()[:8]
        filename = f"{scene_id}_frame{frame}_{code_hash}.png"
        file_path = self.storage_root / filename
        file_path.write_text(f"Remotion preview for {scene_id}")

        render_time_ms = (time.time() - start_time) * 1000

        return RenderResult(
            scene_id=scene_id,
            storage_url=str(file_path),
            width=1080,
            height=1920,
            frame=frame,
            metadata={
                "renderer": "remotion",
                "code_hash": code_hash,
            },
            render_time_ms=render_time_ms,
        )
