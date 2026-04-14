#!/usr/bin/env python3
"""简单的工作流测试，不依赖 LLM"""

import sys
sys.path.insert(0, '.')

from layout.schemas import SceneLayoutSpec, CanvasSpec
from layout.solver import LayoutSolver
from layout.primitives import PrimitiveIntent

def test_layout_generation():
    """测试布局生成流程"""
    print("=== 测试布局生成 ===\n")

    # 创建 canvas
    canvas = CanvasSpec(
        width=1080,
        height=1920,
        safe_top=96,
        safe_right=72,
        safe_bottom=120,
        safe_left=72,
    )
    print(f"✓ Canvas 创建成功: {canvas.width}x{canvas.height}")

    # 创建 intents
    intents = [
        PrimitiveIntent(
            id="title_1",
            primitive_type="HeroTitle",
            role="title",
            text="Python 基础语法",
            importance=10,
        ),
        PrimitiveIntent(
            id="body_1",
            primitive_type="BodyCard",
            role="body",
            text="今天我们来学习 Python 的变量定义和函数调用。",
            importance=8,
        ),
    ]
    print(f"✓ 创建了 {len(intents)} 个 primitive intents")

    # 使用 solver 生成布局
    solver = LayoutSolver()
    layout_spec = solver.solve(
        intents=intents,
        canvas=canvas,
        scene_type="statement",
    )
    print(f"✓ 布局生成成功: {len(layout_spec.elements)} 个元素")

    # 测试 metadata
    layout_spec.metadata["test_key"] = "test_value"
    layout_spec.metadata["intent_source"] = "rules"
    layout_spec.metadata["layout_source"] = "template"
    print(f"✓ Metadata 设置成功: {layout_spec.metadata}")

    # 验证布局
    for i, element in enumerate(layout_spec.elements):
        print(f"  元素 {i+1}: {element.primitive_type} at ({element.box.x:.0f}, {element.box.y:.0f})")

    print("\n=== 所有测试通过 ===")
    return True

if __name__ == "__main__":
    try:
        success = test_layout_generation()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n✗ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
