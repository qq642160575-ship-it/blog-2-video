#!/usr/bin/env python3
"""测试完整的任务流程，检查事件和数据"""

import asyncio
import sys
sys.path.insert(0, '.')

from orchestration.task_context import PipelineResult


def test_pipeline_result():
    """测试 PipelineResult 序列化"""
    print("=== 测试 PipelineResult ===\n")

    result = PipelineResult(
        summary={
            "artifact_count": 6,
            "scene_count": 3,
            "failed_scenes": []
        },
        artifact_ids=["art_1", "art_2", "art_3"],
        scene_artifact_ids=["scene_art_1", "scene_art_2", "scene_art_3"]
    )

    dumped = result.model_dump()
    print("PipelineResult.model_dump():")
    print(dumped)
    print()

    # 验证字段
    assert "summary" in dumped
    assert "artifact_ids" in dumped
    assert "scene_artifact_ids" in dumped
    assert len(dumped["scene_artifact_ids"]) == 3

    print("✓ PipelineResult 包含所有必需字段")
    print("✓ scene_artifact_ids 正确序列化")
    print()


def test_event_payload():
    """测试事件 payload 格式"""
    print("=== 测试事件 Payload ===\n")

    result = PipelineResult(
        summary={"test": "value"},
        artifact_ids=["art_1"],
        scene_artifact_ids=["scene_1", "scene_2"]
    )

    # 模拟 task.completed 事件的 payload
    event_payload = result.model_dump()

    print("task.completed 事件 payload:")
    print(event_payload)
    print()

    # 前端期望的字段
    scene_artifact_ids = event_payload.get("scene_artifact_ids")
    print(f"前端会提取: scene_artifact_ids = {scene_artifact_ids}")
    print(f"类型: {type(scene_artifact_ids)}")
    print(f"长度: {len(scene_artifact_ids) if scene_artifact_ids else 0}")
    print()

    if scene_artifact_ids and len(scene_artifact_ids) > 0:
        print("✓ 前端可以正确提取 scene_artifact_ids")
    else:
        print("✗ 前端无法提取 scene_artifact_ids")
        return False

    return True


if __name__ == "__main__":
    try:
        test_pipeline_result()
        success = test_event_payload()

        if success:
            print("\n=== 所有测试通过 ===")
            sys.exit(0)
        else:
            print("\n=== 测试失败 ===")
            sys.exit(1)
    except Exception as e:
        print(f"\n✗ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
