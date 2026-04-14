# 视频生成后端系统流程完整性修复总结

## 修复概览

本次修复解决了视频生成后端系统流程完整性验证报告中提出的所有高优先级问题，并实现了实时产物回传机制。

---

## 已完成的修复

### 1. 修复变量命名混淆 ✅

**问题**: `visual_strategy` 变量实际存储的是 `VisualProtocol`，与后续生成的 `VisualStrategy` 混淆

**修复位置**: `orchestration/workflow_runner.py:162, 372`

**修复内容**:
```python
# 修复前
visual_strategy = self._normalize(values.get("visual_architect")) or {}

# 修复后
visual_architect_protocol = self._normalize(values.get("visual_architect")) or {}
```

**影响**: 提高代码可读性，避免维护时的逻辑错误

---

### 2. 修复进度百分比回退问题 ✅

**问题**: 进度从 90% 回退到 70%，导致前端进度条倒退

**修复位置**: `orchestration/workflow_runner.py:127-131, 179, 268, 466`

**修复内容**:
```python
# 新的进度分配方案
progress_map = {
    "director_node": ("正在拆分镜头", 20, 1),           # LangGraph: 0-20%
    "visual_architect_node": ("正在设计视觉方案", 40, 2), # LangGraph: 20-40%
    "coder_node": ("正在生成镜头代码", 60, 3),          # LangGraph: 40-60%
}
# M3 增强阶段
# - style_analysis: 65%
# - layout_generation: 70-85%
# - render_preview: 90%
```

**影响**: 进度条平滑递增，用户体验改善

---

### 3. 完善场景数据传递 ✅

**问题**: 场景数据在传递给 LLM 增强组件时仅包含部分字段，丢失了 Director 生成的关键信息

**修复位置**: `orchestration/workflow_runner.py:274-286, 334-344`

**修复内容**:
```python
# 构建完整的场景上下文
scene_context = {
    "scene_id": scene_id,
    "scene_type": scene_type,
    "script": scene.get("script", ""),
    "visual_design": scene.get("visual_design"),      # 新增
    "camera_language": scene.get("camera_language"),  # 新增
    "visual_elements": scene.get("visual_elements"),  # 新增
    "animation_marks": scene.get("animation_marks"),  # 新增
    "duration": scene.get("duration"),                # 新增
}
```

**影响**: LLM 语义提取器和布局设计器能够获得完整的场景上下文，生成质量提升

---

### 4. 修复 SSE 事件流竞态条件 ✅

**问题**: 如果任务在发送历史事件和订阅之间完成，客户端可能收不到 `task.completed` 事件

**修复位置**: `api/routes.py:36-70`

**修复内容**:
```python
# 修复前：先发送历史事件，再订阅
existing = await container.event_repo.list_by_task(task_id)
for event in existing:
    yield _sse(event.model_dump(mode="json"))
queue = await container.event_repo.subscribe_task(task_id)

# 修复后：先订阅，再发送历史事件
queue = await container.event_repo.subscribe_task(task_id)
try:
    existing = await container.event_repo.list_by_task(task_id)
    for event in existing:
        yield _sse(event.model_dump(mode="json"))
    # ... 继续订阅实时事件
finally:
    await container.event_repo.unsubscribe_task(task_id, queue)
```

**影响**: 消除竞态条件，确保客户端接收到所有事件

---

### 5. 规范 node_key 使用 ✅

**问题**: M3 增强阶段使用的 `node_key` 不在 LangGraph 工作流定义中，导致语义混淆

**修复位置**: `wms-video-ide/src/utils/workflowUi.ts:27-68`

**修复内容**:
```typescript
const NODE_LABELS: Record<string, {
  label: string;
  description: string;
  stage: 'langgraph' | 'enhancement'  // 新增 stage 字段
}> = {
  director_node: { ..., stage: 'langgraph' },
  visual_architect_node: { ..., stage: 'langgraph' },
  coder_node: { ..., stage: 'langgraph' },
  style_analysis: { ..., stage: 'enhancement' },      // 标记为增强阶段
  layout_generation: { ..., stage: 'enhancement' },   // 标记为增强阶段
  render_preview: { ..., stage: 'enhancement' },      // 新增
};
```

**影响**: 前端可以区分 LangGraph 节点和自定义增强阶段，便于实现不同的 UI 展示

---

### 6. 实现阶段产物实时回传 ✅

**问题**: 所有阶段的产物都在最后才回传给前端，用户无法实时查看中间结果

**修复位置**: `orchestration/workflow_runner.py:166-210, 460-496`

**修复内容**:

#### 6.1 Script Artifact 实时发布
```python
# LangGraph 执行完成后立即发布
script_artifact = await self.artifact_service.publish_artifact(...)
await self.event_publisher.publish(
    "artifact.published",
    payload={
        "artifact_id": script_artifact.id,
        "artifact_type": "script",
        "summary": "生成脚本文本",
    },
)
```

#### 6.2 Storyboard Artifact 实时发布
```python
storyboard_artifact = await self.artifact_service.publish_artifact(...)
await self.event_publisher.publish(
    "artifact.published",
    payload={
        "artifact_id": storyboard_artifact.id,
        "artifact_type": "storyboard",
        "summary": "生成分镜脚本",
        "scene_count": len(director_scenes),
    },
)
```

#### 6.3 Visual Strategy Artifact 实时发布
```python
visual_artifact = await self.artifact_service.publish_artifact(...)
await self.event_publisher.publish(
    "artifact.published",
    payload={
        "artifact_id": visual_artifact.id,
        "artifact_type": "visual_strategy",
        "summary": f"生成视觉策略 ({visual_strategy_enhanced.style_family})",
        "style_family": visual_strategy_enhanced.style_family,
    },
)
```

#### 6.4 Scene Layout Bundle Artifact 实时发布
```python
layout_bundle_artifact = await self.artifact_service.publish_artifact(...)
await self.event_publisher.publish(
    "artifact.published",
    payload={
        "artifact_id": layout_bundle_artifact.id,
        "artifact_type": "scene_layout_bundle",
        "summary": f"生成 {len(scene_layouts)} 个场景布局",
        "scene_count": len(scene_layouts),
    },
)
```

**影响**: 前端可以在每个阶段完成后立即展示产物，用户体验大幅提升

---

### 7. 实现分镜代码逐个回传 ✅

**问题**: 所有场景代码都在最后批量返回，无法实时查看单个场景的生成结果

**修复位置**: `orchestration/workflow_runner.py:159-176`

**修复内容**:
```python
# 在 LangGraph 更新循环中监听 coder_node 完成事件
async for chunk in iterate_workflow_updates(workflow, initial_state, run_config):
    node_name, node_data = extract_update_node(chunk)

    # 如果是 coder_node 完成，立即发布场景代码事件
    if node_name == "coder_node" and isinstance(normalized_node_data, dict):
        coder_list = normalized_node_data.get("coder", [])
        for coder_item in coder_list:
            if isinstance(coder_item, dict):
                scene_id = coder_item.get("scene_id")
                await self.event_publisher.publish(
                    "scene.code_generated",
                    payload={
                        "scene_id": scene_id,
                        "code": coder_item.get("code"),
                        "summary": f"场景 {scene_id} 代码生成完成",
                    },
                )
```

**影响**:
- 前端可以在每个场景代码生成完成后立即展示
- 用户可以实时查看代码生成进度
- 支持前端实现独立的场景代码 tab 页

---

## 修复效果总结

### 数据流完整性
- ✅ 变量命名清晰，避免混淆
- ✅ 场景数据完整传递，包含所有必需字段
- ✅ 消除 SSE 事件流竞态条件

### 用户体验
- ✅ 进度条平滑递增，不再回退
- ✅ 每个阶段完成后立即展示产物
- ✅ 分镜代码逐个生成，实时可见

### 系统架构
- ✅ 区分 LangGraph 节点和自定义增强阶段
- ✅ 事件类型语义清晰
- ✅ 支持前端实现独立的产物展示 tab 页

---

## 前端集成建议

### 1. 监听 artifact.published 事件
```typescript
// 监听各阶段产物发布事件
eventSource.addEventListener('message', (event) => {
  const data = JSON.parse(event.data);

  if (data.event_type === 'artifact.published') {
    const { artifact_type, artifact_id, summary } = data.payload;

    switch (artifact_type) {
      case 'script':
        // 展示脚本文本
        break;
      case 'storyboard':
        // 展示分镜脚本
        break;
      case 'visual_strategy':
        // 展示视觉策略
        break;
      case 'scene_layout_bundle':
        // 展示场景布局
        break;
    }
  }
});
```

### 2. 监听 scene.code_generated 事件
```typescript
// 监听单个场景代码生成事件
if (data.event_type === 'scene.code_generated') {
  const { scene_id, code, summary } = data.payload;

  // 更新场景代码列表
  updateSceneCode(scene_id, code);

  // 在独立 tab 页展示
  showSceneCodeTab(scene_id, code);
}
```

### 3. 实现产物展示 Tab 页
建议前端实现以下 tab 页结构：
- **脚本** - 展示原始脚本文本
- **分镜** - 展示 Director 生成的分镜脚本
- **视觉策略** - 展示风格、主题、配色方案
- **场景布局** - 展示每个场景的布局设计
- **场景代码** - 展示每个场景的 Remotion 代码（实时更新）

---

## 测试建议

### 1. 进度条测试
- 验证进度从 0% 平滑递增到 100%
- 验证不会出现进度回退

### 2. 实时回传测试
- 验证每个阶段完成后立即收到 artifact.published 事件
- 验证每个场景代码生成后立即收到 scene.code_generated 事件

### 3. SSE 连接测试
- 验证任务快速完成时不会丢失事件
- 验证长时间运行任务的事件连续性

---

## 后续优化建议

### 中优先级
1. 优化 Artifact 层级关系，使用 `related_artifact_ids` 替代严格的 `parent_artifact_id`
2. 添加 `strict_mode` 配置，控制场景失败时的行为
3. 在 Artifact 中记录 fallback 信息，便于前端展示

### 低优先级
1. 增强缓存键，包含模型版本和 prompt 版本
2. 添加工作流元数据字段，存储执行信息
3. 添加 `_normalize()` 方法的递归深度限制

---

## 修改文件清单

1. `orchestration/workflow_runner.py` - 核心修复
2. `api/routes.py` - SSE 竞态条件修复
3. `wms-video-ide/src/utils/workflowUi.ts` - 前端 node_key 规范化

---

## 总结

本次修复解决了报告中提出的所有高优先级问题，并实现了用户要求的实时产物回传机制。系统现在能够：

1. **实时反馈**: 每个阶段完成后立即回传产物
2. **逐个生成**: 分镜代码完成一个回传一个
3. **平滑进度**: 进度条从 0% 平滑递增到 100%，不再回退
4. **数据完整**: 场景数据包含所有必需字段，LLM 生成质量提升
5. **事件可靠**: 消除 SSE 竞态条件，确保客户端接收到所有事件

前端可以基于这些改进实现独立的产物展示 tab 页，为用户提供更好的实时反馈体验。
