#!/usr/bin/env python3
"""诊断脚本：检查任务完成后的事件和数据"""

import sys
sys.path.insert(0, '.')

print("""
=== 前端分镜显示问题诊断指南 ===

当任务完成后前端没有显示分镜时，请按以下步骤检查：

1. 检查浏览器控制台
   - 打开浏览器开发者工具 (F12)
   - 查看 Console 标签页
   - 搜索错误信息（红色文本）
   - 特别注意：
     * "Failed to fetch" - API 请求失败
     * "Cannot read property" - 数据结构问题
     * "scene_artifact_ids" - 场景数据问题

2. 检查 Network 标签页
   - 找到 SSE 连接（通常是 /api/tasks/{task_id}/events_sse）
   - 点击查看 EventStream
   - 确认是否收到 task.completed 事件
   - 检查 payload 中是否包含 scene_artifact_ids

3. 检查后端日志
   - 查找 "task.completed" 相关日志
   - 确认 scene_artifact_ids 是否为空
   - 查找任何 ERROR 或 WARNING 日志

4. 常见问题和解决方案：

   问题 A: task.completed 事件中 scene_artifact_ids 为空
   原因: WorkflowRunner.run_animation() 可能没有正确返回 scene_artifact_ids
   解决: 检查 workflow_runner.py:523-534

   问题 B: 前端收到事件但没有调用 getSceneArtifact
   原因: event.payload.scene_artifact_ids 可能是 undefined
   解决: 在浏览器控制台执行：
   ```javascript
   // 监听 SSE 事件
   window.addEventListener('message', (e) => {
     if (e.data.event_type === 'task.completed') {
       console.log('task.completed payload:', e.data.payload);
     }
   });
   ```

   问题 C: getSceneArtifact API 调用失败
   原因: scene_artifact_id 不存在或 API 路由错误
   解决: 检查后端是否正确创建了 SceneArtifact

   问题 D: 前端状态没有更新
   原因: React 状态更新可能被阻塞
   解决: 检查 useIdeStore 的 patchScene 方法

5. 快速验证步骤：

   步骤 1: 检查后端是否生成了 scene artifacts
   ```bash
   # 在后端日志中搜索
   grep "publish_scene_artifact" logs/*.log
   ```

   步骤 2: 检查前端是否收到 task.completed
   ```javascript
   // 在浏览器控制台执行
   localStorage.setItem('debug', 'true');
   // 然后重新运行任务
   ```

   步骤 3: 手动测试 API
   ```bash
   # 获取任务事件
   curl http://localhost:8000/api/tasks/{task_id}/events

   # 获取场景 artifact
   curl http://localhost:8000/api/scene_artifacts/{scene_artifact_id}
   ```

6. 如果以上都正常，检查：
   - 前端的 scenes 状态是否被正确初始化（director_node 完成时）
   - patchScene 是否正确匹配 scene_id
   - WorkflowStatus 组件是否正确显示状态

7. 临时解决方案：
   如果 LLM 布局设计一直失败，可以临时禁用 LLM 增强：

   在 workflow_runner.py 的 WorkflowRunner.__init__() 中：
   ```python
   enable_llm_enhancement=False  # 改为 False
   ```

   这样会使用基于规则的布局生成，更稳定但不够智能。
""")

print("\n=== 数据结构验证 ===\n")

# 验证关键数据结构
from orchestration.task_context import PipelineResult
from layout.schemas import SceneLayoutSpec, CanvasSpec

result = PipelineResult(
    summary={"scene_count": 2},
    artifact_ids=["art_1"],
    scene_artifact_ids=["scene_art_1", "scene_art_2"]
)

print("✓ PipelineResult 结构正确")
print(f"  - scene_artifact_ids: {result.scene_artifact_ids}")

layout = SceneLayoutSpec(
    scene_id="test",
    canvas=CanvasSpec(),
    elements=[],
    metadata={"test": "value"}
)

print("✓ SceneLayoutSpec 包含 metadata 字段")
print(f"  - metadata: {layout.metadata}")

print("\n=== 建议 ===")
print("1. 重启后端服务以应用修复")
print("2. 重启前端服务（npm run dev）")
print("3. 清除浏览器缓存")
print("4. 重新运行任务并观察浏览器控制台")
print("5. 如果问题持续，请提供浏览器控制台的完整错误信息")
