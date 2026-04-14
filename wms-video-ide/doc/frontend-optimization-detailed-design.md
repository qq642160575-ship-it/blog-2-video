# 前端优化详细设计

## 1. 文档目标

本文档基于当前后端重构结果与 `wms-video-ide` 前端现状，给出前端侧的优化和调整方案，用于指导后续联调与改造落地。

文档目标：

- 明确后端本次改动对前端数据模型、接口调用、状态管理和页面结构的影响。
- 说明当前前端与后端新模型之间的错位点。
- 给出兼容期方案与最终目标方案。
- 将页面、状态、接口、事件流、错误处理、版本管理的改造边界写清楚。

---

## 2. 后端修改内容分析

### 2.1 本次后端重构核心变化

当前后端已经从“直接围绕 LangGraph workflow 组织接口”的模式，演进为“围绕产品级业务实体组织接口”的模式，新增并强化了以下核心对象：

- `session`：一次创作会话，上层业务主上下文。
- `branch`：会话下的版本分支，用于承载版本演进与分叉。
- `task`：异步执行单元，用于驱动创建视频、重生成、修复、预览等任务。
- `artifact`：任务产出物，作为结果事实来源。
- `scene_artifact`：镜头级最小可编辑对象。
- `task_event`：任务事件流，作为进度、时间线、调试信息的统一来源。

### 2.1.1 本次复核结论

重新对照当前代码实现、`ARCHITECTURE.md`、`backend-detailed-design.md`、`backend-rearchitecture-prd.md` 后，可以得出以下结论：

- 当前后端主干方向是正确的，已经从原型式 workflow API 转到了 session-task-artifact 模型。
- 当前后端已经满足“前端开始切换主模型”的最低条件，但还没有完全覆盖 PRD 和详细设计里定义的全部接口与后续能力。
- 因此前端报告不能只写“目标方案”，还必须区分：
  - 已落地、前端可以立即接入的接口
  - 已在后端设计中定义、但当前代码尚未完全实现的接口
  - 前端现在必须预留扩展位、否则后续会再次返工的能力

本次文档优化后的基准判断为：

- `session / task / artifact / scene_artifact / events` 已可作为前端主线接入对象。
- `branch list / branch timeline / scene regenerate task / repair task / render preview task / 冲突控制可视化 / 权限隔离` 仍属于“后续实现需求”，前端需要在设计上预留，但不能假设当前接口已全部可用。

### 2.2 后端新增/强化的接口能力

当前后端已经提供以下新能力：

- `POST /api/sessions`：创建创作会话。
- `GET /api/sessions/{session_id}`：获取会话概览。
- `GET /api/sessions/{session_id}/timeline`：获取 session 时间线。
- `POST /api/sessions/{session_id}/tasks`：在指定分支上创建任务。
- `GET /api/tasks/{task_id}`：获取任务详情。
- `GET /api/tasks/{task_id}/events`：拉取任务事件列表。
- `GET /api/tasks/{task_id}/events_sse`：订阅任务事件流。
- `POST /api/tasks/{task_id}/cancel`：取消任务。
- `POST /api/tasks/{task_id}/retry`：重试失败任务。
- `GET /api/artifacts/{artifact_id}`：获取 artifact。
- `GET /api/scene-artifacts/{scene_artifact_id}`：获取镜头级产物。
- `GET /api/branches/{branch_id}/artifacts`：获取分支下产物列表。
- `POST /api/artifacts/{artifact_id}/branch`：基于某个产物创建新分支。

### 2.2.1 当前实现与设计需求的符合性矩阵

下表区分“当前代码已实现”和“设计文档要求但尚未完全落地”的内容。

| 能力 | 设计要求 | 当前状态 | 对前端的含义 |
| --- | --- | --- | --- |
| 创建 session | 需要 | 已实现 | 可直接接入 |
| 查询 session 概览 | 需要 | 已实现 | 可直接接入 |
| 查询 session timeline | 需要 | 已实现 | 可作为历史主入口 |
| 查询 session branches | 需要 | 未见实际路由实现 | 前端要预留 branch list 结构，当前先不要强依赖 |
| 创建 task | 需要 | 已实现 | 可直接接入 |
| 查询 task | 需要 | 已实现 | 可直接接入 |
| 查询 task events | 需要 | 已实现 | 可用于断线补偿 |
| 订阅 task events SSE | 需要 | 已实现 | 可作为主进度通道 |
| cancel task | 需要 | 已实现 | 前端可接入取消按钮 |
| retry task | 需要 | 已实现 | 前端可接入重试按钮 |
| 查询 artifact | 需要 | 已实现 | 可直接接入 |
| 查询 scene_artifact | 需要 | 已实现 | 可直接接入 |
| branch from artifact | 需要 | 已实现 | 可直接接入分支创建动作 |
| branch artifact history | 需要 | 已实现 | 可直接接入版本历史 |
| branch created event | 设计中要求 | 当前未见显式发布 | 前端不要依赖该事件作为唯一刷新来源 |
| artifact.published event | 设计中要求 | 已实现 | 前端应纳入标准事件适配 |
| validation.failed event | 需要 | 已实现，但 payload 仍偏简化 | 前端先按现有字段兼容，后续预留细化展示 |
| regenerate_scene task 主链路 | 需要 | task_type 已定义，pipeline 未完整接通 | 前端先做入口预留，不要提前锁死请求模型 |
| repair_scene task 主链路 | 需要 | task_type 已定义，未接通 | 前端预留，不直接实现依赖 |
| render_preview task 主链路 | 需要 | task_type 已定义，未接通 | 中栏预留静态预览位 |
| scene version 列表 API | 后续强需求 | 未见独立接口 | 当前需通过 artifact + scene_artifact 组合获取 |
| branch timeline | PRD 明确提到 | 当前只有 session timeline + branch_id 过滤参数 | 前端先按过滤实现，后续再升级独立 branch 视图 |
| 用户归属校验 | 需要 | 数据结构已预留，接口层未完整体现 | 当前报告必须标记为后续需求 |

### 2.3 兼容层的含义

旧接口仍然保留，例如：

- `POST /api/generate_script_sse`
- `POST /api/generate_animation_sse`
- `GET /api/workflows/{workflow}/history`
- `POST /api/workflows/{workflow}/fork_sse`

但其中动画生成接口已经不再直接跑旧前端理解的“纯 workflow 结果流”，而是：

1. 在后端内部创建 `session`
2. 自动创建默认 `branch`
3. 发布源文档 `artifact`
4. 创建 `create_video task`
5. 入队执行
6. 通过 `_stream_legacy_task_events()` 将新任务事件转为旧前端能消费的 SSE 结构

这说明：

- 后端已经把旧接口降级为兼容入口。
- 前端继续长期依赖 `thread_id + checkpoint_id` 会越来越偏离真实后端模型。
- 新前端应以 `session / branch / task / artifact / event` 为主模型。

### 2.4 对后期实现需求的复核结论

对照后端 PRD 和详细设计，当前前端优化报告还需要明确覆盖以下后期需求，否则后续仍会返工：

#### 2.4.1 分支与版本需求

后期不是只需要“从 artifact 创建 branch”，而是需要完整支持：

- branch 列表查询
- branch 切换
- branch 内 artifact 历史
- branch 之间隔离
- branch 乐观锁冲突后的前端提示

当前后端代码已经具备一部分基础对象，但还未把这套能力完全铺平。因此前端报告中不能把 branch 只写成“未来可选功能”，而应视为主模型的固定组成部分。

#### 2.4.2 单镜头重生成与修复需求

PRD 和详细设计明确要求后续支持：

- `regenerate_scene`
- `repair_scene`
- `render_preview`

当前代码层面：

- `TaskType` 已经定义了这些类型
- 但当前真正接通的 pipeline 仍主要是 `create_video`

因此前端设计必须预留：

- 镜头级任务入口
- 镜头级任务状态展示
- 镜头级版本历史
- repair 结果与 validation report 关联展示

#### 2.4.3 时间线需求

后端设计要求 timeline 最终不仅展示 task 进度，还要承载：

- task 过程
- artifact 发布
- validation 失败
- repair 结果
- branch 创建

当前代码里 session timeline 已经可用，但 branch.created 等事件并未全部落齐。前端应把 timeline 适配器设计成“事件类型可扩展”，而不是只支持现在已经看到的 5 到 6 种事件。

#### 2.4.4 冲突控制与阻塞态需求

PRD 和详细设计都写到了：

- branch optimistic lock
- scene 写锁
- blocked 状态
- baseline artifact 校验

当前前端文档原版对此强调不够，现补充结论：

- 前端后续不能只处理 `queued/running/succeeded/failed`
- 还必须预留 `blocked`、`conflict`、`baseline outdated` 这类状态展示位
- 当后端后续补充冲突错误码时，前端不能再做结构性改造，只需要补文案和按钮逻辑

#### 2.4.5 权限与归属需求

PRD 明确要求 session、task、artifact 查询需要校验归属。

当前数据模型中已有 `user_id` 字段，但当前 API 路由实现仍以本地内存仓储为主，权限链路没有完全做完。

因此前端报告里必须增加一个判断：

- 当前前端不要把任意 `session_id / task_id / artifact_id` 视作可自由跨上下文复用
- 所有对象访问都应经过统一 API client 层，便于后续在 401/403/404 上做一致处理

---

## 3. 当前前端现状分析

### 3.1 页面结构

当前前端由三栏构成：

- 左侧 `LeftPanel`：源文本、工作流状态、分镜列表。
- 中间 `PreviewPlayer`：Remotion 播放预览。
- 右侧 `CodeEditor`：代码编辑、进度、历史检查点、日志。

整体页面结构是典型的“单页 IDE”，适合作为后续任务中心继续演进，不需要推翻重做。

### 3.2 当前前端状态模型

`src/store/useIdeStore.ts` 当前核心状态仍围绕旧工作流展开，主要特征如下：

- 用 `scriptThreadId / animationThreadId` 记录两类 workflow 线程。
- 用 `scriptCheckpointId / animationCheckpointId` 记录检查点。
- 用 `historyItemsByWorkflow` 维护 workflow history。
- 用 `workflowProgressByName` 维护以 workflow 名称为粒度的进度。
- 镜头列表 `scenes` 是前端本地聚合结构，不对应后端 `scene_artifact`。

这套状态模型的问题不是不能用，而是建模粒度已经落后于后端。

### 3.3 当前前端接口调用特征

当前前端主要通过以下方式工作：

- 口播改写直接调用 `generate_script_sse`
- 分镜生成直接调用 `generate_animation_sse`
- 历史查看调用 `workflow history`
- 历史恢复调用 `workflow fork_sse`
- SSE 解析后，将 payload 手工映射到 `oralScript`、`scenes`、`code`

当前实现的优势：

- 已经具备流式更新、日志面板、进度反馈、失败重试等基础交互能力。
- 页面结构和体验节奏适合继续向任务中心演进。

当前实现的主要问题：

- 前端把“workflow”当成业务主对象，但后端现在把“task”当成执行主对象。
- 前端把“checkpoint history”当成主要历史能力，但后端现在提供的是“timeline + artifact version + branch”。
- 前端的 `Scene` 是本地临时结构，不带 `scene_artifact_id / artifact_id / version / status / validation_report`。
- 前端无法展示 branch、artifact、scene version，也无法表达任务取消、重试、分叉等真实业务动作。
- `SourceInput` 和 `CodeEditor` 中存在重复 SSE 解析逻辑，接口适配散落。
- 事件消费目前只关注少量 legacy payload，不具备面向新事件模型的扩展性。

---

## 4. 当前前后端错位点

### 4.1 执行主对象错位

当前前端：

- 认为“我在运行一个 workflow”

当前后端：

- 认为“我在执行一个 task，workflow 只是 task 的内部实现”

影响：

- 前端无法准确表示任务状态。
- 前端无法对取消、重试、排队、中断做一致处理。
- 前端日志与时间线无法统一。

### 4.2 历史模型错位

当前前端：

- 依赖 checkpoint history 和 fork replay

当前后端：

- 提供 session timeline、artifact 链、branch 分叉、scene_artifact 版本

影响：

- 当前“历史检查点”面板只能服务旧链路。
- 无法表达“这次结果来自哪个 task、属于哪个 branch、基于哪个 artifact”。
- 无法把“查看历史”与“恢复版本”“创建分支”“比较产物”拆开。

### 4.3 镜头模型错位

当前前端 `Scene`：

- `id`
- `durationInFrames`
- `componentType`
- `script`
- `visual_design`
- `code`
- `marks`

当前后端 `scene_artifact` 已具备：

- `scene_artifact_id`
- `artifact_id`
- `scene_id`
- `scene_order`
- `scene_type`
- `script_text`
- `visual_intent`
- `layout_spec`
- `code_text`
- `validation_report`
- `preview_image_url`
- `status`
- `version`

影响：

- 前端现在只能“显示镜头”，不能“管理镜头版本”。
- 前端缺少镜头状态和验证信息展示位。
- 后续镜头级重生成、修复、回滚没有数据基础。

### 4.4 事件模型错位

当前前端消费的是 legacy SSE：

- `setup`
- `progress`
- `updates`
- `end`
- `error`

当前后端真实事件已经是：

- `task.created`
- `task.queued`
- `task.started`
- `task.progress`
- `workflow.node_completed`
- `validation.failed`
- `task.completed`
- `task.failed`
- `task.cancel_requested`
- `task.cancelled`
- `task.retrying`

影响：

- 当前前端无法无损消费新事件。
- 兼容层一旦裁剪，前端会立即失真。

---

## 5. 前端优化目标

### 5.1 总体目标

前端需要从“workflow IDE”升级为“session-task IDE”，但在短期内保留旧接口兼容能力，避免一次性大改。

### 5.2 设计原则

- 不推翻当前三栏布局，只重构数据流与信息架构。
- 先兼容后收口，允许旧 SSE 与新 Task API 并行一段时间。
- 以 `session / branch / task / artifact / scene_artifact / event` 为统一前端领域模型。
- 页面显示以业务对象为主，不再以 workflow 内部机制为主。
- 任务事件与时间线统一建模，避免日志、进度、历史三套分裂数据。
- 对尚未落地的后端接口与后续需求预留稳定扩展位，避免第二次结构性返工。

---

## 6. 目标前端架构设计

### 6.1 前端分层建议

建议将前端重构为以下分层：

```text
src/
  api/
    client.ts
    sessions.ts
    tasks.ts
    artifacts.ts
    compat.ts
  adapters/
    eventAdapter.ts
    sceneAdapter.ts
    workflowCompatAdapter.ts
  store/
    useSessionStore.ts
    useTaskStore.ts
    useEditorStore.ts
    selectors.ts
  types/
    session.ts
    task.ts
    artifact.ts
    scene.ts
    event.ts
    compat.ts
  hooks/
    useTaskSse.ts
    useSessionTimeline.ts
    useSceneDraft.ts
  components/
    workspace/
    timeline/
    task/
    scene/
    history/
```

说明：

- `api/` 只负责请求。
- `adapters/` 负责把后端响应映射为前端视图模型。
- `store/` 按业务维度拆分，不再把所有状态堆在一个 store 中。
- `hooks/` 负责 SSE 和页面联动。
- `components/` 只消费已经整形好的 view model。

### 6.2 目标状态模型

建议引入三层状态：

#### A. Session 层

负责创作上下文：

- `sessionId`
- `currentBranchId`
- `title`
- `sourceType`
- `sourceContent`
- `userPreference`
- `timelineItems`
- `branchList`

#### B. Task 层

负责异步执行：

- `activeTaskId`
- `tasksById`
- `taskEventsByTaskId`
- `taskProgressByTaskId`
- `pendingTaskIds`
- `lastFailedTaskId`

#### C. Editor 层

负责编辑态：

- `oralScriptDraft`
- `sceneDrafts`
- `activeSceneArtifactId`
- `dirtyFlags`
- `selectedArtifactId`
- `selectedTimelineItemId`

这样可以把“业务事实”和“本地草稿”分开。

---

## 7. 前端核心数据结构设计

### 7.1 SessionViewModel

```ts
type SessionViewModel = {
  sessionId: string;
  currentBranchId: string | null;
  title: string;
  sourceType: string;
  sourceContent: string;
  status: 'active' | 'archived' | 'error';
  userPreference: {
    styleFamily?: string;
    durationSeconds?: number;
  };
};
```

### 7.2 TaskViewModel

```ts
type TaskViewModel = {
  taskId: string;
  sessionId: string;
  branchId: string;
  taskType: 'create_video' | 'regenerate_scene' | 'repair_scene' | 'render_preview';
  status:
    | 'pending'
    | 'queued'
    | 'running'
    | 'succeeded'
    | 'failed'
    | 'cancelled'
    | 'retrying'
    | 'blocked';
  requestPayload: Record<string, unknown>;
  baselineArtifactId: string | null;
  resultSummary: Record<string, unknown>;
  errorCode: string | null;
  errorMessage: string | null;
  cancellationRequested: boolean;
  createdAt: string;
  startedAt: string | null;
  finishedAt: string | null;
};
```

### 7.3 TimelineItemViewModel

```ts
type TimelineItemViewModel = {
  id: string;
  taskId: string;
  branchId: string;
  eventType: string;
  nodeKey?: string | null;
  title: string;
  description: string;
  createdAt: string;
  level: 'info' | 'success' | 'warning' | 'error';
  rawPayload: Record<string, unknown>;
};
```

### 7.4 SceneArtifactViewModel

```ts
type SceneArtifactViewModel = {
  sceneArtifactId: string;
  artifactId: string;
  sceneId: string;
  sceneOrder: number;
  sceneType: string | null;
  scriptText: string;
  visualIntent: Record<string, unknown> | null;
  layoutSpec: Record<string, unknown> | null;
  codeText: string;
  validationReport: Record<string, unknown> | null;
  previewImageUrl: string | null;
  status: 'ready' | 'failed' | 'draft';
  version: number;
  durationInFrames: number;
  marks: Record<string, number>;
};
```

### 7.5 本地草稿结构

本地编辑不能直接覆写服务端事实，建议增加：

```ts
type SceneDraft = {
  sceneArtifactId: string;
  scriptTextDraft: string;
  codeTextDraft: string;
  marksDraft: Record<string, number>;
  durationInFramesDraft: number;
  dirty: boolean;
};
```

意义：

- 服务端返回的是事实版本。
- 编辑器中修改的是草稿版本。
- 后续做“保存为新版本”“重生成前比对差异”“恢复服务端版本”会简单很多。

---

## 8. 接口改造设计

### 8.1 第一阶段：兼容接入

目标：

- 不立即废弃现有生成按钮。
- 新增 session/task 数据层。
- 让前端先能消费新任务事件和新产物结构。

方案：

1. 口播生成仍可暂时走 `generate_script_sse`
2. 动画生成优先改为新链路：
   - `POST /api/sessions`
   - `POST /api/sessions/{sessionId}/tasks`
   - `GET /api/tasks/{taskId}/events_sse`
3. 历史面板新增“任务时间线”视图，旧“检查点历史”先保留

### 8.2 第二阶段：主链路切换

目标：

- 页面主流程全面切换到新 Task API。
- 旧 workflow history/fork 只作为调试入口。

方案：

- 创建视频改为完全基于 `session + create_video task`
- 历史面板默认展示 `session timeline`
- 失败重试统一走 `/api/tasks/{task_id}/retry`
- 取消统一走 `/api/tasks/{task_id}/cancel`
- `artifact.published` 纳入 timeline 与右栏产物刷新逻辑
- `validation.failed` 纳入镜头失败态和任务告警逻辑

### 8.3 第三阶段：去 workflow 中心化

目标：

- 页面不再以 workflow/checkpoint 为主视觉。

方案：

- 去掉默认“历史检查点”主入口
- 将 checkpoint 能力下沉到高级调试区
- 主界面以“任务时间线”“产物版本”“镜头版本”为中心
- 具备 branch 切换、scene 级任务、repair / render_preview 入口

---

## 9. 事件流设计

### 9.1 统一事件适配器

当前必须新增 `eventAdapter.ts`，负责把两类来源统一成同一视图模型：

- 新事件流：`task.* / workflow.node_completed / validation.failed`
- 旧兼容流：`setup / progress / updates / end / error`

统一输出：

- `TaskProgressViewModel`
- `TimelineItemViewModel`
- `ArtifactMutation`
- `SceneMutation`

### 9.2 事件到 UI 的映射规则

#### `task.created`

- 在任务列表中创建任务卡片
- 状态显示“已创建”
- 写入时间线

#### `task.queued`

- 状态显示“排队中”
- 进度条进入等待样式

#### `task.started`

- 状态显示“执行中”
- 开始累计耗时

#### `task.progress`

- 更新进度条
- 更新阶段说明
- 可更新 ETA

#### `workflow.node_completed`

- 作为结构化节点完成事件
- 若 payload 中有镜头/代码数据，更新对应 scene view model
- 写入时间线

#### `artifact.published`

- 刷新当前 branch artifact 列表
- 若为 `script / storyboard / visual_strategy / scene_code_bundle / validation_report`，更新右栏版本视图
- 为后续“从 artifact 创建 branch”提供最新可用对象

#### `validation.failed`

- 将任务标记为有阻塞问题
- 在镜头卡片上标识失败 scene
- 在右侧面板展示验证问题
- 后续当 payload 扩展到结构化 `errors[]` 时，前端不需要改 store 结构，只补展示层

#### `task.completed`

- 状态标记为完成
- 结束计时
- 触发 artifact 列表刷新

#### `task.failed`

- 状态标记为失败
- 展示错误说明
- 暴露“重试任务”入口

#### `task.cancel_requested / task.cancelled`

- 更新按钮为取消中/已取消
- 中断后续自动刷新

### 9.3 SSE Hook 设计

建议新增：

```ts
useTaskSse(taskId, {
  onEvent,
  onProgress,
  onCompleted,
  onFailed,
});
```

职责：

- 建立流式连接
- 解析 `data: ...`
- 调用适配器转成标准事件
- 写入 store
- 自动处理断线和关闭

禁止继续在多个组件里各自复制 `readSse()`。

---

## 10. 页面改造设计

### 10.1 左栏优化

当前左栏结构可保留，但信息语义需要调整。

#### 现状

- `WorkflowStatus` 显示 workflow 维度状态
- `SourceInput` 负责发起生成
- `Timeline` 实际显示的是镜头列表，不是真正时间线

#### 调整方案

左栏拆为三块：

1. `SessionHeader`
   - 会话标题
   - 当前分支
   - 来源类型
   - 用户偏好摘要

2. `TaskStatusCard`
   - 当前活跃任务
   - 状态、耗时、预计剩余时间
   - 取消/重试按钮

3. `SceneListPanel`
   - 镜头列表
   - 镜头状态
   - 校验结果标记
   - 当前版本号

说明：

- 现有 `Timeline` 组件建议重命名为 `SceneListPanel`
- 真正的 timeline 应迁到右栏或单独面板

### 10.2 中栏优化

当前 `PreviewPlayer` 结构可保留，但建议增强：

- 支持按 `scene_artifact` 跳转
- 显示当前 scene 状态
- 当 `preview_image_url` 或后续渲染产物可用时，支持切换“静态预览图 / Remotion 动态预览”
- 若镜头验证失败，在播放器区域给出醒目标识

### 10.3 右栏优化

右栏当前混合了代码、进度、历史、日志，是最适合升级为“任务工作台”的区域。

建议拆分为四个 tab：

- `Code`
- `Task`
- `History`
- `Logs`

#### Code

- 当前镜头代码编辑
- 当前镜头脚本/视觉意图摘要
- 脏数据标记

#### Task

- 当前任务阶段
- 结构化节点完成记录
- 任务参数摘要
- 任务结果摘要

#### History

- Session timeline
- Branch artifact 列表
- Scene version 列表
- 高级区保留 checkpoint 调试入口

#### Logs

- 原始日志流
- 调试信息
- 错误堆栈或错误说明

---

## 11. 镜头模型改造设计

### 11.1 `Scene` 类型替换策略

当前 `src/types/scene.ts` 建议从“纯展示结构”升级为“双层结构”：

```ts
export interface SceneArtifact {
  sceneArtifactId: string;
  artifactId: string;
  sceneId: string;
  sceneOrder: number;
  sceneType: string | null;
  scriptText: string;
  visualIntent: Record<string, unknown> | null;
  layoutSpec: Record<string, unknown> | null;
  codeText: string;
  validationReport: Record<string, unknown> | null;
  previewImageUrl: string | null;
  status: string;
  version: number;
}

export interface SceneDraft {
  sceneArtifactId: string;
  durationInFrames: number;
  marks: Record<string, number>;
  scriptTextDraft: string;
  codeTextDraft: string;
  dirty: boolean;
}
```

页面使用时通过 selector 聚合为 `SceneViewModel`，不要直接让所有组件操作原始接口对象。

### 11.2 镜头列表卡片要新增的信息

当前 `SceneCard` 只显示脚本、视觉文案、时长和 marks。建议新增：

- `sceneArtifactId`
- `version`
- `status`
- `validationReport` 摘要
- `lastGeneratedAt`
- `hasLocalDraft`

### 11.3 镜头失败场景处理

若某个 `scene_artifact.status === failed` 或 `validationReport.passed === false`：

- 卡片高亮为失败状态
- 右栏展示具体失败原因
- 提供“仅重生成该镜头”入口
- 允许用户先查看失败前版本，再决定是否重试

---

## 12. 历史与版本设计

### 12.1 历史能力重构

历史能力要从“检查点历史”升级为“三层历史”：

1. 任务时间线
2. 分支产物历史
3. 镜头版本历史

### 12.2 任务时间线

来源：

- `GET /api/sessions/{session_id}/timeline`

展示内容：

- 任务创建
- 排队
- 开始执行
- 节点完成
- artifact 发布
- 校验失败
- 完成/失败/取消

当前特别说明：

- 当前代码中 `artifact.published` 已经存在，应视为 timeline 主数据。
- `branch.created` 在后端设计中存在，但当前代码未见显式发布；前端当前应在“创建 branch 成功后主动刷新”，不要被动等待事件。

### 12.3 Artifact 历史

来源：

- `GET /api/branches/{branch_id}/artifacts`

展示内容：

- artifact 类型
- version
- summary
- parent_artifact_id
- task_id

### 12.4 Scene 版本历史

短期可通过以下方式构造：

- 读取某个 code bundle artifact
- 再批量读取对应 `scene_artifact`

中期建议后端补充：

- `GET /api/scenes/{scene_id}/artifacts`

用于直接展示镜头版本链。

当前复核结论：

- 该接口尚未实际实现。
- 因此前端当前不要把 scene history 面板与某个未实现接口强绑定。
- 推荐先做“可降级模式”：先按当前 branch 的 artifact + scene_artifact 聚合展示，待后端补齐独立 scene history API 后再替换数据源。

### 12.5 分支能力

当用户对某个 artifact 想“另开一版”时：

- 调用 `POST /api/artifacts/{artifact_id}/branch`
- 前端切换 `currentBranchId`
- 后续所有任务都发往新分支

这会替代当前“从 checkpoint fork”的大部分产品诉求。

---

## 13. 状态管理改造设计

### 13.1 拆分 store

当前单一 `useIdeStore` 承担过多职责，建议拆分：

- `useSessionStore`
- `useTaskStore`
- `useEditorStore`

### 13.2 store 职责划分

#### `useSessionStore`

- session 基础信息
- 当前分支
- timeline
- artifact 列表

#### `useTaskStore`

- task 列表
- active task
- task status
- task events
- progress
- cancel / retry / blocked / conflict UI state

#### `useEditorStore`

- source 文本草稿
- 口播稿草稿
- scene drafts
- active scene
- 面板 UI 状态

### 13.3 selector 设计

建议新增：

- `selectCurrentSession`
- `selectCurrentBranchArtifacts`
- `selectActiveTask`
- `selectTaskProgress`
- `selectSceneViewModels`
- `selectActiveSceneDraft`
- `selectFailedScenes`

这样组件层不会直接拼装业务逻辑。

---

## 14. 兼容迁移方案

### 14.1 迁移策略

采用“三步迁移”：

#### M1：先加新模型，不切主入口

- 增加新类型定义
- 增加 task/session API 封装
- 增加统一 SSE hook 和事件适配器
- 保持旧按钮和旧页面逻辑可用

#### M2：切换动画主链路

- 分镜生成改为 session/task 模式
- 历史面板新增 timeline/artifact 视图
- retry/cancel 接到 task API
- artifact 发布和 validation 失败接入标准事件适配器

#### M3：切换历史主链路

- 历史默认展示 timeline + artifact version
- checkpoint 仅保留在高级调试入口
- branch 视图、scene history、scene task 入口接入

### 14.2 兼容期 UI 策略

兼容期允许同时出现两套信息：

- 面向业务用户：任务、分支、版本、镜头状态
- 面向调试用户：workflow、checkpoint

但默认优先展示前者。

---

## 15. 组件级改造清单

### 15.1 `SourceInput`

调整目标：

- 从直接处理大量 SSE 逻辑，改为只负责发起动作

需要改造：

- 移除组件内 `readSse`
- 发起 `createSession` / `createTask`
- 调用 `useTaskSse`
- 口播生成与视频生成都通过 action 层触发

### 15.2 `WorkflowStatus`

调整目标：

- 重命名并升级为 `TaskStatusCard`

需要改造：

- 输入改为 `activeTask + progress`
- 支持 `queued / running / retrying / cancelled`
- 支持 cancel/retry 操作入口

### 15.3 `Timeline`

调整目标：

- 更名为 `SceneListPanel`

需要改造：

- 绑定 `SceneArtifactViewModel[]`
- 显示版本、状态、验证信息

### 15.4 `CodeEditor`

调整目标：

- 从“代码编辑器 + workflow 历史面板”升级为“任务工作台”

需要改造：

- 历史 tab 改为 timeline/artifact/scene history
- checkpoint history 下沉为 debug 子 tab
- retry/fork 逻辑迁移为 retry task / branch from artifact

### 15.5 `PreviewPlayer`

调整目标：

- 与 `scene_artifact` 对齐

需要改造：

- 接收 scene artifact 聚合视图
- 对失败 scene 提示
- 预留静态预览图展示位

---

## 16. 错误处理与交互设计

### 16.1 错误分类

前端需要区分：

- 请求错误：接口失败、4xx、5xx
- 任务错误：`task.failed`
- 节点错误：某个节点完成异常
- 镜头错误：scene 级校验失败
- 连接错误：SSE 中断

### 16.2 错误呈现原则

- 全局错误只提示动作失败，不堆过多技术信息
- 任务错误展示在任务面板
- 镜头错误展示在镜头卡片和右栏细节
- 调试细节只放日志面板

### 16.3 SSE 断线策略

- 若 task 未进入终态，则提示“连接已断开，正在尝试重新连接”
- 重连后先拉取 `/api/tasks/{task_id}/events`
- 再继续订阅 `/events_sse`
- 通过事件 id 去重，避免重复渲染

说明：

当前后端事件仓储已具备“先查历史、再订阅实时”的能力，前端应充分利用，而不是单纯依赖一次长连接。

---

## 17. 开发执行清单

### 17.1 执行原则

执行时按以下原则推进：

- 先收口数据模型，再调整组件表现。
- 先统一事件和接口层，再拆 store。
- 先切动画主链路，再处理历史与版本视图。
- 对后端尚未完整落地的能力，只做结构预留，不做强绑定实现。

### 17.2 阶段拆分

#### P0：基础收口阶段

目标：

- 消除当前前端中散落的接口和 SSE 处理逻辑。
- 建立后续迁移的最小基础层。

任务清单：

1. 新建 `src/api/` 目录
   - 新增 `client.ts`
   - 新增 `sessions.ts`
   - 新增 `tasks.ts`
   - 新增 `artifacts.ts`
   - 新增 `compat.ts`

2. 新建 `src/types/` 补充模型
   - `session.ts`
   - `task.ts`
   - `artifact.ts`
   - `event.ts`
   - 更新 `scene.ts`

3. 统一 SSE 能力
   - 保留现有 `src/utils/sse.ts`
   - 提取标准 `readSse(response, onPayload)` 为公共实现
   - 新增 `useTaskSse.ts`

4. 新建适配层
   - `eventAdapter.ts`
   - `sceneAdapter.ts`
   - `workflowCompatAdapter.ts`

产出物：

- 前端 API 调用不再散落在组件里
- SSE 解析逻辑只有一份
- 新旧接口都能通过统一适配层消费

依赖：

- 无强后端阻塞，可立即实施

风险：

- 如果仍保留组件内部手工解析 payload，P1 后会继续出现重复逻辑

#### P1：动画主链路切换阶段

目标：

- 将“生成分镜与代码”主链路从 legacy workflow 兼容入口切到 session-task 主链路。

任务清单：

1. 发起动画任务改造
   - 先调用 `POST /api/sessions`
   - 再调用 `POST /api/sessions/{session_id}/tasks`
   - 再订阅 `GET /api/tasks/{task_id}/events_sse`

2. 新建任务视图模型
   - 标准化 `task.created / queued / started / progress / completed / failed`
   - 纳入 `artifact.published`
   - 纳入 `validation.failed`

3. 左栏状态卡切换为 task 视角
   - `WorkflowStatus` 升级为 `TaskStatusCard`
   - 显示 task status、阶段、耗时、重试、取消

4. 右栏日志与进度面板切换为 task 视角
   - 当前进度来自 task event
   - 执行日志来自统一 timeline/event store

产出物：

- 动画主流程不再依赖 `generate_animation_sse`
- 任务取消和重试可直接使用新 API
- `artifact.published` 成为右栏和历史视图刷新依据

依赖：

- 当前后端已满足，具备实施条件

阻塞项：

- 无关键阻塞

#### P2：历史与版本视图切换阶段

目标：

- 将当前“历史检查点”主视图切为“任务时间线 + artifact 历史”。

任务清单：

1. 右栏 History tab 改造
   - 默认展示 session timeline
   - 增加 branch artifact history
   - checkpoint history 下沉为 debug 子视图

2. timeline 展示扩展
   - `task.*`
   - `workflow.node_completed`
   - `artifact.published`
   - `validation.failed`

3. 创建 branch 入口接入
   - 在 artifact 项上提供“从此版本创建分支”
   - 成功后主动刷新 session / branch / artifact 数据

产出物：

- 历史主视图由 workflow history 切换为业务历史
- 版本操作由 checkpoint fork 转向 branch from artifact

依赖：

- `GET /api/sessions/{session_id}/timeline`
- `GET /api/branches/{branch_id}/artifacts`
- `POST /api/artifacts/{artifact_id}/branch`

阻塞项：

- 当前未见 `GET /api/sessions/{session_id}/branches`，branch 列表展示需先做降级处理

降级方案：

- 初期先只管理当前 branch
- branch 创建成功后以前端内存列表追加为主
- 待后端补齐 branch list API 后再切正式数据源

#### P3：镜头模型切换阶段

目标：

- 将前端镜头展示与编辑从本地 `Scene` 结构迁移到 `scene_artifact + scene draft` 双层模型。

任务清单：

1. 改造 `src/types/scene.ts`
   - 区分 `SceneArtifact` 与 `SceneDraft`

2. 改造镜头列表
   - `SceneCard` 展示 `version / status / validation summary`
   - 支持失败态、草稿态、当前版本态

3. 改造右栏代码编辑
   - 编辑对象由 `scene.code` 改为 `sceneDraft.codeTextDraft`
   - 保留服务端 `codeText` 作为对照基线

4. 中栏预览改造
   - 输入改为 `SceneViewModel[]`
   - 预留 `previewImageUrl` 展示位

产出物：

- 镜头状态与版本信息完整进入前端
- 为后续 scene regenerate / repair / preview 铺平数据基础

依赖：

- `GET /api/scene-artifacts/{scene_artifact_id}`

阻塞项：

- 当前缺少独立 scene history API，历史链展示先做聚合降级

#### P4：后续能力预留阶段

目标：

- 为 PRD 中已定义但当前代码未完全落地的能力预埋前端结构。

任务清单：

1. 预留 task type 扩展
   - `regenerate_scene`
   - `repair_scene`
   - `render_preview`

2. 预留状态扩展
   - `blocked`
   - `conflict`
   - `baseline outdated`

3. 预留错误码适配
   - 基于后续后端错误码映射 UI 提示

4. 预留权限处理
   - 在 API client 统一处理 401 / 403 / 404

产出物：

- 后续后端补齐功能时，前端只需补动作，不需重构数据骨架

依赖：

- 依赖后续后端接口补齐，但当前即可先完成类型与 UI 预留

### 17.3 推荐任务拆分到文件

#### 基础层

- `src/api/client.ts`
- `src/api/sessions.ts`
- `src/api/tasks.ts`
- `src/api/artifacts.ts`
- `src/api/compat.ts`
- `src/adapters/eventAdapter.ts`
- `src/adapters/sceneAdapter.ts`
- `src/adapters/workflowCompatAdapter.ts`
- `src/hooks/useTaskSse.ts`
- `src/types/session.ts`
- `src/types/task.ts`
- `src/types/artifact.ts`
- `src/types/event.ts`

#### Store 层

- `src/store/useSessionStore.ts`
- `src/store/useTaskStore.ts`
- `src/store/useEditorStore.ts`
- `src/store/selectors.ts`

#### 组件层

- `src/components/LeftPanel/SourceInput.tsx`
- `src/components/LeftPanel/WorkflowStatus.tsx`
- `src/components/LeftPanel/Timeline.tsx`
- `src/components/LeftPanel/SceneCard.tsx`
- `src/components/PreviewPlayer/index.tsx`
- `src/components/CodeEditor/index.tsx`

### 17.4 后端依赖与阻塞清单

#### 当前已可依赖

- `POST /api/sessions`
- `GET /api/sessions/{session_id}`
- `GET /api/sessions/{session_id}/timeline`
- `POST /api/sessions/{session_id}/tasks`
- `GET /api/tasks/{task_id}`
- `GET /api/tasks/{task_id}/events`
- `GET /api/tasks/{task_id}/events_sse`
- `POST /api/tasks/{task_id}/cancel`
- `POST /api/tasks/{task_id}/retry`
- `GET /api/artifacts/{artifact_id}`
- `GET /api/scene-artifacts/{scene_artifact_id}`
- `GET /api/branches/{branch_id}/artifacts`
- `POST /api/artifacts/{artifact_id}/branch`

#### 当前应视为未完全可依赖

- `GET /api/sessions/{session_id}/branches`
- 独立 scene history API
- `regenerate_scene` 的 task 主链路
- `repair_scene` 的 task 主链路
- `render_preview` 的 task 主链路
- branch created 标准事件
- 结构化冲突错误码
- 权限校验完整链路

### 17.5 排期建议

建议按以下顺序排期：

1. P0 基础收口
2. P1 动画主链路切换
3. P2 历史与版本视图切换
4. P3 镜头模型切换
5. P4 后续能力预留

说明：

- 如果资源紧张，至少要先完成 P0 + P1，否则前端仍会继续沉淀旧模型技术债。
- 如果需要尽快支撑版本/回溯能力，优先推进 P2。
- 如果后端准备开始做 scene regenerate / repair，则 P3 不应再后推。

## 18. 验收标准

### 18.1 功能验收

- 可以通过新接口创建 session 和 task
- 可以在前端实时看到 task 状态变化
- 可以看到 session timeline
- 可以按 branch 查看 artifacts
- 镜头列表可以显示 scene_artifact 的状态和版本
- 失败任务可以 retry
- 运行中任务可以 cancel
- 兼容期内旧入口仍可工作

补充符合性验收：

- 当前文档不得假设 `GET /api/sessions/{session_id}/branches` 已存在
- 当前文档不得假设 scene history 独立接口已存在
- 当前文档必须覆盖 `artifact.published` 事件
- 当前文档必须为 `blocked`、冲突、baseline 过期预留状态位
- 当前文档必须把 `regenerate_scene / repair_scene / render_preview` 视作后续固定扩展点，而不是可有可无的优化项

### 18.2 体验验收

- 进度信息只有一套主来源，不再在多个面板冲突
- 历史信息可区分“任务历史”和“调试检查点”
- 用户能看懂“当前正在执行什么、结果属于哪个版本、失败发生在哪个镜头”

### 18.3 代码质量验收

- 不再在多个组件中复制 SSE 解析逻辑
- API、adapter、store、component 职责分离
- 旧 workflow 兼容逻辑被隔离到 `compat` 层

---

## 19. 推荐实施顺序

### 第一批

- 新建 `doc/` 文档
- 补充 `types/session.ts`、`types/task.ts`、`types/artifact.ts`、`types/event.ts`
- 提取统一 `readSse` 和 `useTaskSse`
- 新建 API 封装层

### 第二批

- 拆 store
- 接入 `session + task + events_sse`
- 左栏状态卡改为 task 视角
- 右栏新增 timeline/artifact 视图

### 第三批

- 镜头模型全面切换到 `scene_artifact`
- 接入 branch from artifact
- 历史默认切换到新模型
- checkpoint history 下沉为调试功能

---

## 20. 结论

当前后端已经完成从 workflow 原型向任务系统的关键转向，而前端仍停留在 workflow/checkpoint 心智模型。前端优化的重点不在于重画 UI，而在于把现有三栏 IDE 的数据骨架升级到 `session / branch / task / artifact / scene_artifact / event`。

短期应采取兼容迁移方案，先把动画生成主链路接到新 task system，再逐步把历史、版本、镜头编辑统一到新模型上。中长期应让 checkpoint 退到调试层，把任务时间线、artifact 版本和 scene 版本作为前端主视图。

补充复核结论：

- 当前后端实现已经足够支撑前端开始主模型迁移，但还不足以宣称“已完整满足后端所有接口需求和后期需求”。
- 更准确的结论应该是：主骨架已到位，接口层仍处于“部分实现 + 部分预留”的阶段。
- 因此前端优化报告必须同时服务两件事：
  - 指导当前可落地改造
  - 约束未来接口补齐时不再引发前端结构返工
