# 问题修复总结

## 已修复的问题

### 1. 后端布局生成参数错误 ✅
**文件**: `video-back/layout/solver.py:89-93`

**问题**: 调用 `estimate_lines()` 时传入了 4 个参数，但方法只接受 3 个
```python
# 错误的调用
estimated_lines = self.text_metrics.estimate_lines(
    intent.text,
    spec.min_font_size,
    width - spec.default_padding * 2,
    "sans-serif",  # ← 多余的参数
)
```

**修复**: 移除了多余的 `"sans-serif"` 参数
```python
# 正确的调用
estimated_lines = self.text_metrics.estimate_lines(
    intent.text,
    spec.min_font_size,
    width - spec.default_padding * 2,
)
```

---

### 2. SceneLayoutSpec 缺少 metadata 字段 ✅
**文件**: `video-back/layout/schemas.py:63`

**问题**: `SceneLayoutSpec` 没有 `metadata` 字段，导致运行时错误
```python
# 错误：'SceneLayoutSpec' object has no attribute 'metadata'
layout_spec.metadata["intent_source"] = "llm"
```

**修复**: 添加了 `metadata` 字段
```python
class SceneLayoutSpec(BaseModel):
    scene_id: str
    canvas: CanvasSpec = Field(default_factory=CanvasSpec)
    elements: list[LayoutElement]
    metadata: dict[str, Any] = Field(default_factory=dict)  # ← 新增
```

---

### 3. 前端进度条显示问题 ✅
**文件**: `wms-video-ide/src/adapters/eventAdapter.ts:43`

**问题**: `description` 字段被错误地设置为 `payload.label`
```typescript
// 错误
description: (payload.label as string | undefined) || fallback.description,
```

**修复**: 改为使用 `fallback.description`
```typescript
// 正确
description: fallback.description,
```

---

### 4. LLM 布局设计 Prompt 改进 ✅
**文件**: `video-back/generation/llm_agents/layout_designer.py:119-177`

**问题**: LLM 返回单个元素对象而非完整的 `LayoutDesignResult` 结构

**修复**:
1. 改进了 prompt，明确要求返回完整的 JSON 结构
2. 添加了 JSON 示例模板
3. 改进了错误日志，便于调试

```python
**重要：你必须返回一个包含以下所有字段的 JSON 对象：**

{
  "elements": [...],
  "composition": "...",
  "visual_hierarchy": [...],
  "focal_point": "...",
  "design_reasoning": "...",
  "estimated_density": "..."
}
```

---

## 验证步骤

### 1. 重启服务
```bash
# 重启后端（如果使用 PyCharm，点击重启按钮）
# 或者如果使用命令行：
# pkill -f "python.*main.py"
# python main.py

# 重启前端
cd wms-video-ide
npm run dev
```

### 2. 清除缓存
- 浏览器：按 Ctrl+Shift+Delete，清除缓存
- 或者使用无痕模式

### 3. 测试流程
1. 输入原文
2. 生成口播稿
3. 生成分镜和代码
4. 观察：
   - 进度条是否正常显示（不回退）
   - 是否有布局生成错误
   - 任务完成后是否显示分镜

### 4. 检查日志
**后端日志关键信息**:
```
✓ 正常: "Structured invoke success operation=layout_design:Scene X"
✗ 错误: "Structured invoke failed operation=layout_design:Scene X"
✗ 错误: "Failed to generate layout for scene Scene X"
```

**前端控制台关键信息**:
```
✓ 正常: "已生成 N 个分镜"
✓ 正常: task.completed 事件包含 scene_artifact_ids
✗ 错误: "Failed to fetch"
✗ 错误: "Cannot read property"
```

---

## 如果问题仍然存在

### 问题 A: LLM 布局设计持续失败
**临时解决方案**: 禁用 LLM 增强，使用规则引擎

编辑 `video-back/main.py` 或 `video-back/app/dependencies.py`:
```python
workflow_runner = WorkflowRunner(
    artifact_service=artifact_service,
    artifact_repo=artifact_repo,
    event_publisher=event_publisher,
    enable_llm_enhancement=False,  # ← 改为 False
)
```

### 问题 B: 前端没有显示分镜
**诊断步骤**:
1. 打开浏览器开发者工具 (F12)
2. 切换到 Network 标签页
3. 找到 SSE 连接 (`/api/tasks/{task_id}/events_sse`)
4. 查看 EventStream，确认是否收到 `task.completed` 事件
5. 检查 payload 中是否包含 `scene_artifact_ids`

**手动测试 API**:
```bash
# 获取任务事件
curl http://localhost:8000/api/tasks/{task_id}/events

# 获取场景 artifact
curl http://localhost:8000/api/scene_artifacts/{scene_artifact_id}
```

### 问题 C: 进度条仍然回退
**检查点**:
- 确认前端代码已更新（`eventAdapter.ts`）
- 清除浏览器缓存
- 检查是否有多个前端实例在运行

---

## 系统流程验证报告中的高优先级问题

根据之前的流程验证报告，以下是需要后续修复的高优先级问题：

### 1. 进度百分比回退问题
**当前状态**: 部分修复（前端 description 已修复）
**待修复**: 重新规划进度百分比映射

建议修改 `workflow_runner.py:127-131`:
```python
progress_map = {
    "director_node": ("正在拆分镜头", 20, 1),      # 改为 20%
    "visual_architect_node": ("正在设计视觉方案", 40, 2),  # 改为 40%
    "coder_node": ("正在生成镜头代码", 60, 3),     # 改为 60%
}
# M3 阶段使用 65%, 70-85%, 90%
```

### 2. 变量命名混淆
**待修复**: `workflow_runner.py:162`
```python
# 建议重命名
visual_architect_protocol = self._normalize(values.get("visual_architect")) or {}
visual_strategy = VisualStrategy(...)  # M3 增强的策略
```

### 3. 场景数据传递不完整
**待修复**: `workflow_runner.py:274-287`

建议传递完整的场景上下文：
```python
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

---

## 测试清单

- [x] 布局生成不再报参数错误
- [x] SceneLayoutSpec 可以设置 metadata
- [x] 前端进度条 description 正确显示
- [x] LLM prompt 包含完整的 JSON 结构示例
- [ ] 完整流程测试：原文 → 口播稿 → 分镜 → 显示
- [ ] 验证 LLM 布局设计成功率
- [ ] 验证前端正确显示所有分镜
- [ ] 验证进度条不再回退

---

## 相关文件清单

### 后端修改
- `video-back/layout/solver.py` - 修复参数错误
- `video-back/layout/schemas.py` - 添加 metadata 字段
- `video-back/generation/llm_agents/layout_designer.py` - 改进 prompt

### 前端修改
- `wms-video-ide/src/adapters/eventAdapter.ts` - 修复 description 字段

### 测试文件
- `video-back/test_workflow_simple.py` - 基础布局测试
- `video-back/test_complete_flow.py` - 完整流程测试
- `video-back/diagnose_frontend_issue.py` - 诊断脚本
