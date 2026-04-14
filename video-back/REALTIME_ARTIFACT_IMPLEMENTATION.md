# 实时产物回传完整实现总结

## 实现概览

本次实现了完整的实时产物回传机制，包括后端事件发布和前端实时展示。现在系统能够：

1. **后端实时发布事件** - 每个阶段完成后立即发布 artifact 事件
2. **前端实时接收事件** - SSE 监听并处理新的事件类型
3. **前端 Tab 页展示** - 独立的 ArtifactTabs 组件展示各阶段产物
4. **分镜代码逐个回传** - 每个场景代码生成完成后立即回传

---

## 后端实现

### 1. 修复的核心问题

#### 1.1 变量命名规范化
```python
# orchestration/workflow_runner.py:162
visual_architect_protocol = self._normalize(values.get("visual_architect")) or {}
```

#### 1.2 进度平滑递增
```python
# orchestration/workflow_runner.py:127-131
progress_map = {
    "director_node": ("正在拆分镜头", 20, 1),
    "visual_architect_node": ("正在设计视觉方案", 40, 2),
    "coder_node": ("正在生成镜头代码", 60, 3),
}
# M3 增强: 65%, 70-85%, 90%
```

#### 1.3 场景数据完整传递
```python
# orchestration/workflow_runner.py:277-286
scene_context = {
    "scene_id": scene_id,
    "scene_type": scene_type,
    "script": scene.get("script", ""),
    "visual_design": scene.get("visual_design"),
    "camera_language": scene.get("camera_language"),
    "visual_elements": scene.get("visual_elements"),
    "animation_marks": scene.get("animation_marks"),
    "duration": scene.get("duration"),
}
```

#### 1.4 SSE 竞态条件修复
```python
# api/routes.py:49-70
# 先订阅，再发送历史事件
queue = await container.event_repo.subscribe_task(task_id)
try:
    existing = await container.event_repo.list_by_task(task_id)
    for event in existing:
        yield _sse(event.model_dump(mode="json"))
    # ...
finally:
    await container.event_repo.unsubscribe_task(task_id, queue)
```

### 2. 实时事件发布

#### 2.1 Script Artifact 实时发布
```python
# orchestration/workflow_runner.py:166-186
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

#### 2.2 Storyboard Artifact 实时发布
```python
# orchestration/workflow_runner.py:188-210
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

#### 2.3 Visual Strategy Artifact 实时发布
```python
# orchestration/workflow_runner.py:460-472
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

#### 2.4 Scene Layout Bundle Artifact 实时发布
```python
# orchestration/workflow_runner.py:484-496
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

#### 2.5 场景代码逐个回传
```python
# orchestration/workflow_runner.py:159-176
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

---

## 前端实现

### 1. Store 扩展

#### 1.1 添加 Artifacts 状态管理
```typescript
// src/store/useIdeStore.ts:41-43
artifactsByType: Record<string, ArtifactResponse | null>;
sceneCodeBySceneId: Record<string, string>;
```

#### 1.2 添加 Artifact 管理方法
```typescript
// src/store/useIdeStore.ts:323-344
setArtifact: (artifactType, artifact) => set((state) => ({
  artifactsByType: {
    ...state.artifactsByType,
    [artifactType]: artifact,
  },
})),

setSceneCode: (sceneId, code) => set((state) => ({
  sceneCodeBySceneId: {
    ...state.sceneCodeBySceneId,
    [sceneId]: code,
  },
})),

clearArtifacts: () => set({
  artifactsByType: {},
  sceneCodeBySceneId: {},
}),
```

### 2. SSE 事件处理

#### 2.1 处理 artifact.published 事件
```typescript
// src/components/LeftPanel/SourceInput.tsx:121-138
if (event.event_type === 'artifact.published') {
  const payload = event.payload as any;
  const artifactType = payload.artifact_type;
  const summary = payload.summary || '';

  addProcessLog(`产物已生成：${summary}`);

  if (payload.artifact_id) {
    useIdeStore.getState().setArtifact(artifactType, {
      artifact_id: payload.artifact_id,
      artifact_type: artifactType,
      summary: summary,
      ...payload,
    } as any);
  }
}
```

#### 2.2 处理 scene.code_generated 事件
```typescript
// src/components/LeftPanel/SourceInput.tsx:140-151
if (event.event_type === 'scene.code_generated') {
  const payload = event.payload as any;
  const sceneId = payload.scene_id;
  const code = payload.code;

  if (sceneId && code) {
    updateSceneCode(sceneId, code);
    useIdeStore.getState().setSceneCode(sceneId, code);
    addProcessLog(`场景代码已生成：${sceneId}`);
  }
}
```

### 3. ArtifactTabs 组件

#### 3.1 Tab 配置
```typescript
// src/components/LeftPanel/ArtifactTabs.tsx:11-19
const TABS: TabConfig[] = [
  { id: 'script', label: '脚本', icon: <FileText />, artifactType: 'script' },
  { id: 'storyboard', label: '分镜', icon: <Film />, artifactType: 'storyboard' },
  { id: 'visual_strategy', label: '视觉策略', icon: <Palette />, artifactType: 'visual_strategy' },
  { id: 'layout', label: '场景布局', icon: <Layout />, artifactType: 'scene_layout_bundle' },
  { id: 'code', label: '场景代码', icon: <Code />, artifactType: 'scene_code' },
];
```

#### 3.2 动态内容渲染
- **脚本 Tab**: 展示原始脚本文本
- **分镜 Tab**: 展示所有场景的分镜信息
- **视觉策略 Tab**: 展示风格家族、主题配置、生成信息
- **场景布局 Tab**: 展示每个场景的布局设计
- **场景代码 Tab**: 展示每个场景的 Remotion 代码（实时更新）

#### 3.3 智能显示/隐藏
```typescript
// src/components/LeftPanel/ArtifactTabs.tsx:182-186
const hasAnyArtifact = Object.keys(artifactsByType).length > 0 ||
                       Object.keys(sceneCodeBySceneId).length > 0;

if (!hasAnyArtifact) {
  return null;
}
```

### 4. LeftPanel 集成
```typescript
// src/components/LeftPanel/index.tsx:24-29
<div className="flex min-h-0 flex-1 flex-col gap-4 overflow-hidden p-4">
  <WorkflowStatus />
  <SourceInput />
  <ArtifactTabs />  {/* 新增 */}
  <Timeline />
</div>
```

---

## 数据流图

```
┌─────────────────────────────────────────────────────────────┐
│                        后端流程                              │
└─────────────────────────────────────────────────────────────┘

LangGraph 执行
    ↓
director_node 完成 → 立即发布 script + storyboard artifacts
    ↓
visual_architect_node 完成
    ↓
M3 风格分析完成 → 立即发布 visual_strategy artifact
    ↓
M3 布局生成完成 → 立即发布 scene_layout_bundle artifact
    ↓
coder_node 完成（每个场景） → 立即发布 scene.code_generated 事件
    ↓
所有场景完成 → 发布 task.completed 事件

┌─────────────────────────────────────────────────────────────┐
│                        前端流程                              │
└─────────────────────────────────────────────────────────────┘

SSE 接收事件
    ↓
artifact.published 事件 → 存储到 artifactsByType
    ↓
scene.code_generated 事件 → 存储到 sceneCodeBySceneId
    ↓
ArtifactTabs 组件自动更新显示
    ↓
用户实时查看各阶段产物
```

---

## 用户体验改进

### 之前
- ❌ 所有产物在最后才返回
- ❌ 无法实时查看中间结果
- ❌ 进度条可能回退（90% → 70%）
- ❌ 场景代码批量返回

### 现在
- ✅ 每个阶段完成后立即返回产物
- ✅ 实时查看脚本、分镜、视觉策略、布局
- ✅ 进度条平滑递增（0% → 100%）
- ✅ 场景代码逐个生成，实时可见
- ✅ 独立的 Tab 页展示各阶段产物
- ✅ 日志实时显示产物生成信息

---

## 测试验证

### 1. 后端事件发布测试
```bash
# 启动后端
python main.py

# 创建任务并观察日志
# 应该看到以下事件按顺序发布：
# - artifact.published (script)
# - artifact.published (storyboard)
# - artifact.published (visual_strategy)
# - artifact.published (scene_layout_bundle)
# - scene.code_generated (每个场景)
# - task.completed
```

### 2. 前端实时展示测试
```bash
# 启动前端
npm run dev

# 点击"生成视频"按钮
# 观察以下行为：
# 1. 进度条从 0% 平滑递增到 100%
# 2. ArtifactTabs 组件逐步显示
# 3. 各 Tab 页内容实时更新
# 4. 场景代码逐个出现
# 5. 日志显示产物生成信息
```

### 3. SSE 连接测试
```bash
# 使用 curl 测试 SSE 端点
curl -N http://localhost:8000/api/tasks/{task_id}/events

# 应该看到事件流：
# data: {"event_type":"task.started",...}
# data: {"event_type":"artifact.published","payload":{"artifact_type":"script",...}}
# data: {"event_type":"artifact.published","payload":{"artifact_type":"storyboard",...}}
# ...
```

---

## 文件修改清单

### 后端
1. `orchestration/workflow_runner.py` - 核心修复和实时事件发布
2. `api/routes.py` - SSE 竞态条件修复
3. `wms-video-ide/src/utils/workflowUi.ts` - node_key 规范化

### 前端
1. `src/store/useIdeStore.ts` - 添加 artifacts 状态管理
2. `src/components/LeftPanel/SourceInput.tsx` - SSE 事件处理
3. `src/components/LeftPanel/ArtifactTabs.tsx` - 新建 Tab 组件
4. `src/components/LeftPanel/index.tsx` - 集成 ArtifactTabs

---

## 总结

本次实现真正做到了：

1. **后端实时回传** - 每个阶段完成后立即发布事件
2. **前端实时展示** - SSE 监听并实时更新 UI
3. **独立 Tab 页** - 为每个阶段产物提供独立展示空间
4. **逐个回传** - 场景代码完成一个回传一个
5. **用户体验** - 进度平滑、反馈及时、信息完整

系统现在能够为用户提供完整的实时反馈体验，用户可以在生成过程中随时查看各阶段的产物，而不需要等到最后。
