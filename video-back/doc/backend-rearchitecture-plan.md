# 后端重构方案

## 1. 文档目标

这份文档给当前 `blog-2-video` 后端提供一套不受现有实现束缚的重构方案，重点解决三个核心问题：

1. 生成画面仍会溢出，提示词约束不稳定
2. 生成画面的视觉语言单一，UI 质感偏低
3. 回溯系统不适合多用户、多任务并发，缺少真正可用的 session / task 体系

文档目标不是解释当前代码怎么工作，而是定义下一代后端应该如何设计，方便后续按阶段实施。


## 2. 现状诊断

### 2.1 当前主链路

当前动画生成主链路位于 [workflow/animation_work_flow.py](E:/奇思妙想/blog-2-video/video-back/workflow/animation_work_flow.py)，大体为：

- `director_node`
- `visual_architect_node`
- `coder_node`
- `qa_guard`

它的特点是：

- 依赖 LLM 直接输出较多中间结果
- 布局、风格、代码生成都由模型主导
- 后端缺少严格的程序级验收
- 回溯依赖 LangGraph checkpoint

### 2.2 当前实现的根本问题

#### 问题一：约束主要停留在 prompt 层

虽然 [prompts/visual_architect.yaml](E:/奇思妙想/blog-2-video/video-back/prompts/visual_architect.yaml) 和 [prompts/coder.yaml](E:/奇思妙想/blog-2-video/video-back/prompts/coder.yaml) 已经加入 safe area、字号、层级、时序等 hard rules，但这类规则目前主要通过语言约束生效，而不是通过程序校验生效。

当前缺失：

- 旋转后 bbox 越界检测
- 文本实际排版后的高度检测
- 元素重叠与碰撞检测
- 层级与 reveal order 一致性检查
- 渲染后首帧/关键帧视觉验收
- 自动 repair 闭环

结果是：

- 模型“知道”不能溢出
- 但系统“不保证”不会溢出

#### 问题二：视觉生成空间被后端过度限制

当前 Director 和 Visual Architect 的提示词把视觉语言锁定在一种偏 `Vizplainer / LogicCard / Stamp / Connector` 的表达上。这个方向适合做一类说明型视频，但不适合作为所有内容的默认风格。

当前缺失：

- 风格路由层
- 主题系统
- 视觉 primitive 库
- 素材层
- 场景类型分类
- 视觉质量验收指标

结果是：

- 模型会收敛到最容易稳定输出的低成本信息图
- 大量依赖边框、贴纸、线条、icon 补画面
- 视频更像“模板拼图”，不是“镜头化表达”

#### 问题三：当前回溯是 checkpoint，不是任务系统

当前 runtime 位于 [workflow/runtime.py](E:/奇思妙想/blog-2-video/video-back/workflow/runtime.py)，运行时实际使用的是 `InMemorySaver`，而不是生产级任务存储。

虽然项目已有 [utils/persistent_checkpointer.py](E:/奇思妙想/blog-2-video/video-back/utils/persistent_checkpointer.py)，但它本质上还是把整块内存状态序列化后落入 SQLite，不适合：

- 多用户并发
- 多任务并发
- 多实例部署
- 按 session/task 查询
- 细粒度回溯
- 审计
- 权限隔离

结果是：

- “能回放状态”不等于“产品级可追溯”
- checkpoint 更像底层恢复机制，而不是上层业务模型


## 3. 重构目标

新的后端应该满足以下目标。

### 3.1 业务目标

- 支持从文章到视频的完整生产链路
- 支持多用户、多 session、多任务并发
- 支持 scene 级别重生成、分支、回滚
- 支持结果质量闭环，而不是单轮生成
- 支持后续接入素材、渲染、TTS、字幕、导出

### 3.2 工程目标

- 把“生成”与“验收”解耦
- 把“语义结构”与“几何布局”解耦
- 把“任务状态”与“工作流 checkpoint”解耦
- 把“风格决策”与“具体代码生成”解耦
- 把“在线状态”与“可追溯历史”解耦

### 3.3 架构原则

1. LLM 负责语义与创意，不负责最终几何正确性
2. 程序负责布局求解、约束校验和修复
3. 渲染结果必须进入验收闭环
4. session / task / artifact 是业务主对象
5. checkpoint 只是引擎内部恢复机制


## 4. 目标架构总览

建议将后端拆成 6 层。

### 4.1 API 层

职责：

- 接收前端请求
- 创建 session / task
- 返回 task_id
- 提供 SSE / WebSocket 事件流
- 提供 artifact、history、branch 查询

建议接口风格：

- `POST /api/sessions`
- `GET /api/sessions/{session_id}`
- `POST /api/sessions/{session_id}/tasks`
- `GET /api/tasks/{task_id}`
- `POST /api/tasks/{task_id}/cancel`
- `POST /api/artifacts/{artifact_id}/branch`
- `GET /api/sessions/{session_id}/timeline`

### 4.2 Orchestrator 层

职责：

- 决定某类 task 走哪条 pipeline
- 启动 LangGraph 或其他工作流
- 协调事件写入
- 控制重试、取消、超时、幂等

这一层不要直接暴露给前端，它服务于任务执行。

### 4.3 Generation 层

职责：

- 脚本改写
- 分镜规划
- 风格决策
- 视觉意图生成
- scene primitive 组装
- Remotion code 生成

这一层可以继续使用多 agent，也可以逐步调整 agent 边界。

### 4.4 Validation / Repair 层

职责：

- 布局约束校验
- 文本可读性校验
- 动画时序校验
- 结构完整性校验
- 渲染结果截图验收
- 自动 repair

这层必须程序优先，不能只靠 prompt。

### 4.5 Artifact 层

职责：

- 存储每个阶段的结构化产物
- 管理 scene 版本、branch、diff
- 为回溯和编辑提供稳定对象

artifact 应该成为产品主数据，而不是临时中间态。

### 4.6 Infra 层

职责：

- PostgreSQL
- Redis
- 对象存储
- 任务队列
- 渲染 worker
- 日志与指标


## 5. 核心业务对象设计

建议把当前系统围绕以下对象建模。

### 5.1 Session

含义：

- 用户围绕一篇文章/一个视频项目的一次完整创作上下文

建议字段：

- `id`
- `user_id`
- `title`
- `source_type`
- `source_content`
- `status`
- `current_branch_id`
- `created_at`
- `updated_at`

说明：

- session 是顶层容器
- 一个 session 下可以有多个 branch
- 一个 branch 下可以有多轮生成和修改任务

### 5.2 Branch

含义：

- 对 session 内容的一个可独立演化的版本分支

建议字段：

- `id`
- `session_id`
- `parent_branch_id`
- `base_artifact_id`
- `name`
- `created_from_task_id`
- `created_at`

说明：

- branch 用于“从某个时刻开始重做”
- 回溯体验应该主要围绕 branch，而不是 checkpoint

### 5.3 Task

含义：

- 一次明确的系统执行动作

任务类型示例：

- `rewrite_script`
- `generate_storyboard`
- `generate_visual_strategy`
- `generate_scene_layouts`
- `generate_scene_code`
- `validate_scene`
- `repair_scene`
- `render_preview`
- `regenerate_scene`

建议字段：

- `id`
- `session_id`
- `branch_id`
- `task_type`
- `status`
- `priority`
- `requested_by`
- `request_payload`
- `result_summary`
- `error_message`
- `started_at`
- `finished_at`

### 5.4 TaskRun

含义：

- 某个 task 的一次实际执行记录

建议字段：

- `id`
- `task_id`
- `attempt`
- `worker_name`
- `workflow_name`
- `workflow_run_id`
- `status`
- `started_at`
- `finished_at`

说明：

- 一个 task 可以多次重试
- task 是业务对象，task_run 是执行对象

### 5.5 TaskEvent

含义：

- 任务执行过程中的事件流

事件示例：

- `task_created`
- `workflow_started`
- `director_completed`
- `style_router_completed`
- `layout_validation_failed`
- `repair_applied`
- `preview_render_completed`
- `task_failed`
- `task_completed`

建议字段：

- `id`
- `task_id`
- `task_run_id`
- `session_id`
- `branch_id`
- `event_type`
- `event_level`
- `node_key`
- `payload`
- `created_at`

说明：

- 前端时间线主要读这张表
- SSE 也主要从事件表或事件总线推送

### 5.6 Artifact

含义：

- 每个阶段可被消费、编辑、对比、回退的结构化结果

artifact 类型示例：

- `source_document`
- `script_v1`
- `storyboard_v1`
- `visual_strategy_v1`
- `scene_layout_bundle_v1`
- `scene_code_bundle_v1`
- `preview_image`
- `rendered_video`
- `validation_report`

建议字段：

- `id`
- `session_id`
- `branch_id`
- `task_id`
- `artifact_type`
- `artifact_subtype`
- `version`
- `content_json`
- `content_text`
- `storage_url`
- `summary`
- `created_at`

### 5.7 SceneArtifact

含义：

- scene 级别的独立可编辑产物

建议字段：

- `id`
- `artifact_id`
- `scene_id`
- `scene_order`
- `script_text`
- `visual_intent`
- `layout_spec`
- `code_text`
- `validation_report`
- `preview_image_url`
- `status`

说明：

- scene 必须成为一等公民
- 否则 scene 级重生成、diff、repair 会持续别扭


## 6. 推荐的数据库模型

建议主数据使用 PostgreSQL。

### 6.1 为什么不用 checkpoint 做主存储

因为 checkpoint 天然存在以下问题：

- 偏引擎内部结构，不稳定
- 不利于跨版本迁移
- 不利于多维查询
- 不利于做权限
- 不利于做审计
- 不利于做人类可理解的时间线

### 6.2 推荐表

最小集合：

- `users`
- `sessions`
- `branches`
- `tasks`
- `task_runs`
- `task_events`
- `artifacts`
- `scene_artifacts`
- `render_jobs`

可选增强：

- `task_locks`
- `prompt_profiles`
- `theme_profiles`
- `asset_references`
- `quality_scores`
- `usage_metrics`


## 7. 新的生成链路设计

当前链路过于“直接”。建议改为下面这条更稳定的链路。

### 7.1 建议链路

`Source Ingest`
-> `Script Rewrite`
-> `Storyboard Planning`
-> `Style Routing`
-> `Scene Intent Generation`
-> `Constraint-based Layout Solve`
-> `Code Generation from Primitives`
-> `Static Validation`
-> `Preview Render`
-> `Visual Validation`
-> `Repair / Retry`
-> `Artifact Publish`

### 7.2 每一层的职责

#### 7.2.1 Script Rewrite

输入：

- 原文

输出：

- 适合视频讲述的 script artifact

注意：

- 只做语言改写，不做分镜、不做布局

#### 7.2.2 Storyboard Planning

输入：

- script artifact

输出：

- 每个 scene 的叙事目标
- 重点语义
- 信息密度
- 时长建议
- 是否需要图像/图表/UI/screenshot

注意：

- 不在这一步直接指定具体像素布局

#### 7.2.3 Style Routing

输入：

- storyboard
- 内容类型
- 用户偏好

输出：

- `visual_style_family`
- `theme_profile`
- `asset_policy`
- `composition_policy`

可选风格族：

- editorial typography
- product UI
- cinematic explainer
- collage mixed media
- brutal poster
- diagrammatic minimal

这一步是解决“所有画面都像一个模板”的关键。

#### 7.2.4 Scene Intent Generation

输入：

- scene 叙事信息
- style family
- theme profile

输出：

- scene intent
- primitive 列表
- 信息层级
- reveal order
- 需要的素材类型

注意：

- 这里输出的是“设计意图”
- 不直接输出最终绝对坐标

#### 7.2.5 Constraint-based Layout Solve

输入：

- scene intent
- 可用 primitives
- 文字长度
- 画布尺寸
- safe area 规则

输出：

- 稳定的 layout spec

建议 solver 负责：

- 区域划分
- 文本框估算
- 元素放置
- 碰撞避免
- zIndex 与 reveal order 对齐
- 长文本自动拆分

这是解决溢出的第一关键层。

#### 7.2.6 Code Generation from Primitives

输入：

- layout spec
- theme profile
- motion profile

输出：

- scene code

建议：

- coder 不再自由手写所有结构
- coder 主要负责把标准 primitive 转成 Remotion 代码
- 尽量从受控组件模板生成，而不是从零即兴生成

#### 7.2.7 Static Validation

检查内容：

- 布局越界
- 文本容器溢出
- reveal order 不一致
- marks 冲突
- 缺少 render
- 缺少关键字段

#### 7.2.8 Preview Render

输出：

- scene 首帧图
- 关键帧图
- 可选低清预览视频

#### 7.2.9 Visual Validation

检查内容：

- 文字是否过小
- 是否被遮挡
- 视觉重心是否失衡
- 是否过于空洞
- 是否退化为线框/UI 拼凑

这里可引入程序规则 + 视觉模型联合验收。

#### 7.2.10 Repair / Retry

repair 顺序建议：

1. 先程序修复布局
2. 再回到 scene intent 重新布局
3. 最后才整体重生成 scene

这样能显著减少代价。


## 8. 布局系统重构方案

这是当前最值得优先重构的部分。

### 8.1 不要再让 LLM 直接决定最终像素坐标

建议把布局拆成两层：

- 语义布局层
- 几何求解层

### 8.2 语义布局层输出内容

由 LLM 输出：

- 主体块有哪些
- 哪块优先级最高
- 哪块可以并排
- 哪块必须压在上层
- 哪块适合做配图
- 哪块必须大字号

示例字段：

- `role: hero_title`
- `role: supporting_fact`
- `role: quote`
- `role: screenshot`
- `role: chart`
- `importance: 1..5`
- `preferred_region: upper / center / lower`
- `group_with`
- `must_follow`

### 8.3 几何求解层输出内容

由程序生成：

- `x`
- `y`
- `width`
- `height`
- `padding`
- `font_size`
- `line_height`
- `z_index`

### 8.4 布局求解器要处理的问题

- 1080x1920 画布边界
- safe area
- 文本行数
- 字号底线
- 卡片最小尺寸
- 旋转带来的 bbox 扩张
- 阴影额外占位
- 元素间最小距离
- 视觉平衡

### 8.5 建议的布局策略

第一版可以先做规则求解：

- 区块网格切分
- 文本高度估算
- 优先级驱动分配
- 旋转限制在轻微范围
- stamp 仅作为辅助装饰

后续可升级：

- simulated annealing
- constraint solver
- ILP
- heuristic packing

### 8.6 文本溢出校验

必须单独做，不要混在别的检查里。

检查项：

- 按 font_size / line_height / width 估算行数
- 文本容器高度是否足够
- 是否超出最多 2 到 3 行
- 是否需要自动拆卡

repair 策略：

- 扩大容器
- 重新分区
- 拆成多卡
- 升级为多 beat scene


## 9. 视觉系统重构方案

### 9.1 从“单风格 prompt”升级为“视觉策略系统”

建议引入 `visual_strategy` artifact，包含：

- `style_family`
- `theme_profile`
- `motion_profile`
- `asset_policy`
- `scene_type_mapping`

### 9.2 Theme Profile 结构建议

建议字段：

- `theme_id`
- `name`
- `font_heading`
- `font_body`
- `color_background`
- `color_primary`
- `color_secondary`
- `color_text`
- `surface_style`
- `corner_radius_scale`
- `shadow_style`
- `stroke_style`
- `motion_style`

### 9.3 Primitive 库

建议不要让 coder 从零造所有结构，而是维护 scene primitive 库。

建议初始 primitive：

- `HeroTitle`
- `BodyCard`
- `QuoteCard`
- `StatPanel`
- `MetricGrid`
- `StepTimeline`
- `ComparisonSplit`
- `ScreenshotFrame`
- `ChartCard`
- `TerminalSnippet`
- `ImageStage`
- `CalloutTag`

原则：

- 线条和 icon 只能辅助，不应主导画面
- 大字排版、截图、图像、图表、强块面必须成为主表达

### 9.4 场景类型路由

scene planner 需要先判断场景类型，再决定 visual strategy。

建议 scene type：

- `statement`
- `contrast`
- `process`
- `timeline`
- `data_point`
- `product_demo`
- `quote`
- `emotion_peak`

不同 scene type 映射不同 primitive 组合，而不是都走 LogicCard。

### 9.5 素材系统

长期上建议接入素材层：

- 图片生成
- 截图生成
- 图表生成
- 代码截图
- terminal 截图
- 品牌图标库

artifact 里要能记录素材来源与引用关系。


## 10. 验收与修复闭环

这部分是稳定性的核心。

### 10.1 三层验收

建议做三层验收。

#### 第一层：结构验收

检查：

- schema 是否完整
- scene 是否缺字段
- marks 是否合法
- primitive 是否可渲染

#### 第二层：几何验收

检查：

- safe area
- bbox
- collision
- text overflow
- layering
- time ordering

#### 第三层：视觉验收

检查：

- 字够不够大
- 主次是否清晰
- 是否太空
- 是否太挤
- 是否廉价图标化
- 是否符合主题

### 10.2 Repair 优先级

建议 repair 从低成本到高成本：

1. 纯布局修复
2. 文本拆分与容器调参
3. primitive 替换
4. scene intent 局部重生成
5. 整个 scene 重生成

### 10.3 Repair 结果也要入库

每一次 repair 都应成为 artifact 和 event，而不是悄悄覆盖。

这样后续可以：

- 对比 repair 前后结果
- 统计最常见失败原因
- 反向优化 prompt 与 solver


## 11. 回溯系统重构方案

### 11.1 从 checkpoint history 改为 session timeline

前端不应该直接感知 checkpoint。

前端应该看到的是：

- session
- branch
- task timeline
- scene versions
- artifact versions

### 11.2 推荐的回溯体验

用户可以：

- 查看这个 session 发生过哪些任务
- 查看每个任务产出了哪些 artifact
- 从任意 artifact 创建新 branch
- 对比两个 branch 的 scene 差异
- 回退到任意 scene 版本继续编辑

### 11.3 checkpoint 的定位

checkpoint 仍然有价值，但应降级为：

- 工作流恢复
- 长任务中断恢复
- agent 执行恢复

而不是作为：

- 用户产品级历史
- 业务主存储

### 11.4 你提到的 `a[session_id].doctor...` 思路如何落地

这个方向可以落成“session scoped runtime context”：

- `session_runtime_context`
  - `script_state`
  - `storyboard_state`
  - `visual_strategy_state`
  - `scene_state_map`
  - `task_state_map`
  - `branch_state`

但不建议把它直接做成进程内字典。

建议：

- 内存里可做热缓存
- 真正权威状态写 PostgreSQL / Redis
- 每个 task 有独立上下文快照


## 12. 任务系统设计

### 12.1 任务队列

建议引入：

- Redis + Celery
- 或 Redis + RQ
- 或 PostgreSQL + 自建 worker

优先目标：

- 异步执行
- 支持重试
- 支持取消
- 支持并发限制
- 支持任务优先级

### 12.2 为什么要把 LangGraph 放进任务系统，而不是反过来

因为 LangGraph 擅长编排节点，不擅长天然承担：

- 多租户任务中心
- 任务优先级
- 取消与抢占
- 历史审计
- 业务事件模型

更合理的做法是：

- 任务系统负责调度
- LangGraph 负责单任务内部 agent 编排

### 12.3 推荐执行模型

1. API 创建 task
2. task 进入队列
3. worker 拉取 task
4. worker 启动具体 pipeline
5. pipeline 每个阶段写 event 和 artifact
6. SSE/WebSocket 将 event 推给前端
7. 完成后更新 task status


## 13. LangGraph 在新架构中的位置

LangGraph 不需要被移除，但角色应该收缩。

### 13.1 适合继续保留的部分

- script rewrite 内部多步推理
- storyboard planning 内部循环
- scene generation 的 agent 协作
- repair 流程的局部编排

### 13.2 不适合继续交给 LangGraph 直接承担的部分

- 产品级历史
- 业务权限模型
- 多任务调度
- 长期 artifact 存储
- 跨 session 的查询

### 13.3 推荐关系

- `TaskSystem -> invokes WorkflowRunner`
- `WorkflowRunner -> drives LangGraph`
- `LangGraph -> emits structured stage output`
- `ArtifactStore / EventStore -> persist results`


## 14. 新的模块拆分建议

建议后端目录逐步调整为：

```text
video-back/
  api/
    routes/
    schemas/
  app/
    config.py
    dependencies.py
  domain/
    sessions/
    tasks/
    artifacts/
    scenes/
  orchestration/
    task_dispatcher.py
    workflow_runner.py
    event_publisher.py
  pipelines/
    script_pipeline/
    storyboard_pipeline/
    animation_pipeline/
    repair_pipeline/
  generation/
    director/
    style_router/
    scene_intent/
    codegen/
  layout/
    primitives.py
    solver.py
    text_metrics.py
    validator.py
    repair.py
  rendering/
    preview_renderer.py
    visual_validator.py
  persistence/
    models/
    repositories/
  workers/
    task_worker.py
    render_worker.py
  infra/
    db/
    cache/
    queue/
```

### 14.1 关键模块职责

`domain/`

- 定义业务对象和状态变化规则

`orchestration/`

- 管任务执行，不写业务规则

`generation/`

- 负责 LLM 和生成逻辑

`layout/`

- 负责几何和文本约束

`rendering/`

- 负责截图和视觉验收

`persistence/`

- 负责数据库读写


## 15. API 重构建议

### 15.1 Session API

- `POST /api/sessions`
- `GET /api/sessions/{session_id}`
- `GET /api/sessions/{session_id}/branches`
- `POST /api/sessions/{session_id}/branches`

### 15.2 Task API

- `POST /api/sessions/{session_id}/tasks`
- `GET /api/tasks/{task_id}`
- `GET /api/tasks/{task_id}/events`
- `POST /api/tasks/{task_id}/cancel`
- `POST /api/tasks/{task_id}/retry`

### 15.3 Artifact API

- `GET /api/artifacts/{artifact_id}`
- `GET /api/scene-artifacts/{scene_artifact_id}`
- `POST /api/artifacts/{artifact_id}/branch`
- `GET /api/sessions/{session_id}/timeline`

### 15.4 SSE / WebSocket

建议不要只流 raw workflow updates。

建议推送标准事件：

- `task.created`
- `task.started`
- `task.progress`
- `task.artifact_published`
- `task.validation_failed`
- `task.repair_applied`
- `task.completed`
- `task.failed`


## 16. 缓存策略重构

当前 `.cache` 是全局文件缓存，容易出现：

- 多用户污染
- prompt 变更后旧缓存误命中
- branch 切换语义错误
- 不易统计

### 16.1 新缓存 key 设计

建议至少带上：

- `model_role`
- `prompt_version`
- `session_id`
- `branch_id`
- `scene_id`
- `input_hash`

### 16.2 缓存分层

- 短期热缓存：Redis
- 长期可复用 artifact：PostgreSQL + 对象存储

### 16.3 哪些内容不建议只放缓存

- scene code
- validation report
- preview image
- repair result

这些应该是 artifact，不只是 cache。


## 17. 并发与隔离设计

### 17.1 并发原则

- session 之间天然隔离
- branch 之间逻辑隔离
- task 之间可并发，但要有冲突控制

### 17.2 典型冲突场景

- 同一 scene 被两个 regenerate task 同时修改
- 同一 branch 被多个任务同时写新 artifact
- 同一 session 被用户回滚时仍有旧任务在跑

### 17.3 建议控制策略

- branch 级乐观锁
- scene 级写锁
- task 创建时记录基线 artifact version
- 提交 artifact 时校验基线是否已过期

### 17.4 多实例部署要求

必须避免依赖：

- 进程内内存作为主状态
- 本地磁盘作为唯一事实源

应该统一走：

- PostgreSQL
- Redis
- 对象存储


## 18. 可观测性设计

### 18.1 日志

每个日志至少带：

- `session_id`
- `branch_id`
- `task_id`
- `task_run_id`
- `scene_id`
- `node_key`

### 18.2 指标

建议收集：

- 每类 task 成功率
- 每类 scene 失败率
- repair 触发率
- overflow 检测命中率
- 风格族分布
- 平均生成时长
- 平均 render 时长

### 18.3 质量面板

长期建议做一个质量 dashboard，追踪：

- 哪类 scene 最常溢出
- 哪类 primitive 最容易出问题
- 哪类主题最容易退化为简陋 UI


## 19. 分阶段迁移方案

建议分四期，不要一次性全量推翻。

### 19.1 第一期：补稳定性底座

目标：

- 不改产品形态，先解决最痛的溢出与不可追踪问题

工作项：

- 接入真正的 `layout_validator`
- 接入 `repair` 节点
- scene 输出改成明确的 `scene_artifact`
- 把 task event 流抽象出来
- 统一 UTF-8 编码
- 给现有缓存增加 prompt_version

阶段结果：

- 即使视觉风格还一般，至少结果更稳

### 19.2 第二期：引入 session / task / artifact 主模型

目标：

- 从 checkpoint 驱动转向产品对象驱动

工作项：

- 建 PostgreSQL 表
- 引入 session / branch / task / artifact repository
- 让前端开始读取 timeline 而不是直接读 workflow history
- checkpoint 降级为内部恢复层

阶段结果：

- 回溯能力大幅提升
- 多用户可用性明显增强

### 19.3 第三期：重构视觉系统

目标：

- 解决画面风格单一和简陋问题

工作项：

- 加 style router
- 加 theme profile
- 建 primitive 库
- scene planner 输出 scene type
- coder 改为基于 primitive 生成

阶段结果：

- 画面上限明显提升

### 19.4 第四期：引入渲染与视觉验收闭环

目标：

- 让结果质量形成闭环

工作项：

- 自动预览渲染
- 截图验收
- 视觉模型评分
- repair 与 retry 策略联动

阶段结果：

- 系统从“会生成”进化到“会自检”


## 20. 技术选型建议

### 20.1 推荐保留

- FastAPI
- Pydantic
- LangGraph
- Remotion

### 20.2 推荐新增

- PostgreSQL
- Redis
- Celery 或 RQ
- 对象存储
- 图像渲染 worker

### 20.3 不建议继续依赖的方式

- `InMemorySaver` 作为主历史来源
- 全局文件缓存作为主状态来源
- 只靠 prompt 保证布局正确
- 只靠 coder 即兴生成所有视觉结构


## 21. 推荐优先级

如果只能先做三件事，建议按下面顺序：

1. 做布局 validator + repair
2. 做 session / task / artifact 数据模型
3. 做 style router + primitive 库

原因：

- 第一步解决结果稳定性
- 第二步解决产品可用性
- 第三步解决结果上限


## 22. 最终建议

下一代后端不应继续被定义为“一个多 agent 工作流”。

它更准确的定义应该是：

“一个以 session 为核心、以 task 为执行单元、以 artifact 为事实来源、以 validation/repair 为质量闭环的视频生成系统。”

在这个体系里：

- LangGraph 是执行引擎的一部分
- LLM 是生成器的一部分
- prompt 是策略的一部分
- 但真正保证产品可用的，是任务系统、artifact 系统、布局求解系统和验收系统

这四块搭起来之后，你现在提的三个问题才会真正进入可持续解决状态，而不是靠不断补 prompt。
