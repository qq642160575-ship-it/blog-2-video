# 后端重构 PRD

## 1. 文档信息

| 项目 | 内容 |
| --- | --- |
| 文档名称 | blog-2-video 后端产品化重构 PRD |
| 关联方案 | `video-back/doc/backend-rearchitecture-plan.md` |
| 关联后端 | `video-back` |
| 当前版本 | v1.0 |
| 文档目标 | 将后端从 workflow demo 升级为可追溯、可并发、可验收、可迭代的视频生成系统 |

## 2. 背景与问题

当前 `blog-2-video` 后端已经具备基础的文章到视频生成原型，主入口位于 `main.py`，API 路由位于 `api/routes.py`，核心动画链路位于 `workflow/animation_work_flow.py`。现有链路大体为：

1. `director_node` 生成分镜。
2. `visual_architect_node` 生成全局视觉协议。
3. `coder_node` 并发生成每个 scene 的 Remotion 代码。
4. `qa_guard` 对代码做基础可用性检查。
5. `workflow_service.py` 通过 SSE 将 workflow updates 和进度信息推给前端。

现有能力证明了多 Agent 生成路径可行，但它仍然以 LangGraph workflow 和 checkpoint 为中心，而不是以产品对象为中心。随着需求从原型验证进入产品化，当前架构暴露出三个核心问题。

### 2.1 画面约束停留在 prompt 层

`prompts/visual_architect.yaml` 和 `prompts/coder.yaml` 中已经加入 safe area、字号、层级、时序等约束，但约束主要依赖模型遵守。系统缺少独立的程序级验收能力，导致模型即使知道不能溢出，最终结果仍可能出现：

- 文字容器高度不足。
- 元素超出 1080x1920 画布或安全区。
- 旋转后的 bbox 越界。
- 元素重叠、遮挡、层级冲突。
- reveal order 与 zIndex 不一致。
- 渲染后首帧或关键帧不可读。

### 2.2 视觉生成空间过窄

当前视觉表达容易收敛到 `Vizplainer / LogicCard / Stamp / Connector` 一类说明型信息图，适合部分科普说明场景，但不适合作为所有内容的默认表达。当前缺少：

- style router。
- theme profile。
- scene type 分类。
- primitive 库。
- 素材引用层。
- 视觉质量验收指标。

这会让生成结果过度依赖边框、贴纸、线条和 icon 补画面，视频更像模板拼图，而不是面向内容的镜头化表达。

### 2.3 回溯能力是 checkpoint，不是产品级任务系统

当前 API 暴露了 `/api/workflows/{workflow_name}/history`、`replay_sse`、`fork_sse` 等基于 checkpoint 的历史能力。`workflow/runtime.py` 中运行时实际使用 `InMemorySaver`，虽然已有 `utils/persistent_checkpointer.py`，但其本质仍是把 LangGraph 内部状态序列化到 SQLite。

这种方式适合工作流恢复，不适合作为业务主存储。它无法很好支持：

- 多用户隔离。
- 多 session 并发。
- 多任务并发调度。
- 按 session、task、scene、artifact 查询。
- 细粒度回滚、分支和 diff。
- 审计、权限和后续数据迁移。

## 3. 产品定位

重构后的后端不再被定义为“一个多 Agent 工作流”，而应定义为：

> 一个以 session 为核心、以 task 为执行单元、以 artifact 为事实来源、以 validation / repair 为质量闭环的视频生成系统。

在这个体系中：

- LangGraph 是单任务内部的编排引擎。
- LLM 是语义、创意和代码生成器。
- Prompt 是生成策略的一部分。
- Task、Artifact、Layout、Validation、Repair 是产品稳定性的核心保障。

## 4. 目标与非目标

### 4.1 总目标

本次重构要把当前后端从“能生成”升级为“可稳定生产、可追溯、可局部重做、可并发扩展”。

### 4.2 业务目标

- 支持从文章到视频的完整生产链路，覆盖脚本、分镜、视觉策略、scene 布局、scene 代码、校验、预览和修复。
- 支持多用户、多 session、多 task 并发。
- 支持 scene 级重生成、修复、版本查看、对比和分支。
- 支持从任意 artifact 创建 branch，避免覆盖式回滚。
- 支持任务进度、失败原因、修复记录和产物历史的前端可视化。
- 为后续接入素材、TTS、字幕、渲染导出预留稳定扩展点。

### 4.3 工程目标

- 将任务状态与 LangGraph checkpoint 解耦。
- 将语义结构与几何布局解耦。
- 将风格决策与代码生成解耦。
- 将生成结果与验收结果解耦。
- 将缓存与产品主数据解耦。
- 将在线运行状态与长期可追溯历史解耦。

### 4.4 非目标

本 PRD 不要求一次性交付以下能力：

- 完整商业化权限、团队管理和计费。
- 完整素材版权管理。
- 全自动成片导出平台。
- 多人实时协作编辑。
- 高级美学评分 dashboard。
- 一次性替换所有现有 workflow。

## 5. 当前系统基线

### 5.1 当前 API

当前主要 API 包括：

- `GET /api/workflows`
- `GET /api/workflows/{workflow_name}/history`
- `POST /api/workflows/{workflow_name}/replay_sse`
- `POST /api/workflows/{workflow_name}/fork_sse`
- `POST /api/workflows/animation/regenerate_scene_sse`
- `POST /api/generate_script_sse`
- `POST /api/generate_animation_sse`

当前请求模型主要包括：

- `GenerateRequest`: `source_text`, `thread_id`
- `ReplayRequest`: `thread_id`, `checkpoint_id`
- `ForkRequest`: `thread_id`, `checkpoint_id`, `values`, `as_node`
- `RegenerateSceneRequest`: `thread_id`, `scene_id`, `script`, `visual_design`

### 5.2 当前 workflow 状态

动画 workflow 的 `State` 当前包含：

- `script`
- `director`
- `visual_architect`
- `coder`
- `failed_scenes`
- `max_parallel_coders`
- `last_action`

这说明当前状态仍以 workflow 内部节点产物为中心，缺少稳定的业务对象，例如 session、branch、task、artifact、scene artifact。

### 5.3 当前缓存与回溯

当前缓存由 `utils/cache.py` 提供，使用 `.cache/{hash}.json` 文件存储。cache key 由 agent name、scene json、visual architect json 等组成，尚未显式包含：

- `prompt_version`
- `session_id`
- `branch_id`
- `scene_id`
- `artifact_version`

当前回溯依赖 LangGraph checkpoint。`PersistentInMemorySaver` 可将 checkpoint 序列化到 SQLite，但它不是结构化业务存储，不适合直接作为产品历史。

## 6. 用户与场景

### 6.1 用户类型

| 用户 | 需求 |
| --- | --- |
| 视频创作者 | 输入文章，稳定生成脚本、分镜、场景代码和预览结果 |
| 场景编辑者 | 对某个 scene 进行局部编辑、重生成、回滚和对比 |
| 内部调试者 | 查看任务进度、Agent 输出、失败原因、repair 记录 |
| 前端开发者 | 通过稳定 API 获取 session、timeline、artifact、scene、task event |
| 后端开发者 | 基于清晰对象模型扩展队列、渲染、TTS、字幕、素材系统 |

### 6.2 核心用户故事

#### US-01 从文章创建视频生成 session

用户输入一篇文章，希望系统创建一个 session，并异步生成脚本、分镜、视觉策略、scene 代码和可预览结果。

验收条件：

- 系统返回 `session_id` 和首个 `task_id`。
- 前端可以通过 task event 流展示进度。
- 每个阶段产物都保存为 artifact。
- 任务完成后 session timeline 可查看完整过程。

#### US-02 查看任务执行进度

用户希望看到当前任务执行到哪一步，是否失败，失败原因是什么。

验收条件：

- 前端可以通过 SSE 或 WebSocket 收到标准事件。
- 事件至少包含 `session_id`、`branch_id`、`task_id`、`event_type`、`payload`、`created_at`。
- 失败事件包含结构化错误码和可读错误信息。

#### US-03 单 scene 局部重生成

用户对某个 scene 不满意，希望只重做该 scene，不影响其他 scene。

验收条件：

- scene 作为 `SceneArtifact` 独立存在。
- 重生成任务带有基线 artifact 版本。
- 新结果写成新的 scene artifact 版本，不直接覆盖旧版本。
- timeline 可展示本次 scene 重生成任务。

#### US-04 从历史 artifact 创建分支

用户希望从一个旧结果继续修改，而不是覆盖当前版本。

验收条件：

- 任意可分支 artifact 可创建 branch。
- branch 记录 `parent_branch_id` 和 `base_artifact_id`。
- 新 branch 内的任务和 artifact 不污染原 branch。
- 前端可以查询 branch 列表和 branch 时间线。

#### US-05 自动修复布局错误

系统生成 scene 后发现文本溢出或元素越界，希望自动修复。

验收条件：

- validator 输出结构化报告。
- repair 按低成本优先策略执行。
- repair 前后 artifact 都保留。
- repair 事件可在 timeline 中查看。

#### US-06 多任务并发执行

多个用户或多个 session 同时生成视频。

验收条件：

- task 由队列或任务系统调度。
- session 之间状态隔离。
- 同一 branch 的冲突写入被检测。
- worker 异常不导致业务历史丢失。

## 7. 产品范围

### 7.1 本期必须包含

- Session / Branch / Task / TaskRun / TaskEvent / Artifact / SceneArtifact 主模型。
- 标准 task event 流。
- scene 级 artifact 化。
- 布局 validator。
- repair 闭环初版。
- visual strategy artifact。
- style router 和 theme profile 初版。
- primitive 库初版。
- checkpoint 降级为内部恢复机制。

### 7.2 本期建议包含

- PostgreSQL 作为主数据存储。
- Redis + Celery 或 Redis + RQ 作为任务队列。
- 对象存储抽象，用于 preview image、rendered video 等大文件。
- Timeline API。
- Branch API。
- Task cancel / retry API。

### 7.3 本期可延后

- 完整视频导出。
- TTS、字幕和音画同步。
- 高级素材库。
- 多租户权限与计费。
- 美学模型训练和质量 dashboard。

## 8. 核心对象模型

### 8.1 Session

含义：用户围绕一篇文章或一个视频项目的一次完整创作上下文。

建议字段：

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `id` | string | session 唯一 ID |
| `user_id` | string | 所属用户 |
| `title` | string | session 标题 |
| `source_type` | enum | `text/url/markdown` 等 |
| `source_content` | text | 原始输入 |
| `status` | enum | `active/archived/error` |
| `current_branch_id` | string | 当前默认分支 |
| `created_at` | datetime | 创建时间 |
| `updated_at` | datetime | 更新时间 |

规则：

- session 是顶层容器。
- session 下可以有多个 branch。
- session 不直接存放所有生成结果，生成结果由 artifact 承载。

### 8.2 Branch

含义：session 内容的一个可独立演化版本。

建议字段：

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `id` | string | branch 唯一 ID |
| `session_id` | string | 所属 session |
| `parent_branch_id` | string nullable | 父分支 |
| `base_artifact_id` | string nullable | 创建分支时的基线 artifact |
| `name` | string | 分支名称 |
| `created_from_task_id` | string nullable | 创建来源任务 |
| `head_artifact_id` | string nullable | 当前 head |
| `version` | int | 乐观锁版本 |
| `created_at` | datetime | 创建时间 |

规则：

- branch 用于“从某个时刻开始重做”。
- branch 写入 artifact 时需要校验基线版本。
- branch 之间默认互不覆盖。

### 8.3 Task

含义：用户或系统发起的一次明确执行动作。

任务类型初版：

- `create_video`
- `rewrite_script`
- `generate_storyboard`
- `generate_visual_strategy`
- `generate_scene_intent`
- `solve_scene_layout`
- `generate_scene_code`
- `validate_scene`
- `repair_scene`
- `render_preview`
- `regenerate_scene`
- `create_branch`

建议字段：

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `id` | string | task 唯一 ID |
| `session_id` | string | 所属 session |
| `branch_id` | string | 所属 branch |
| `task_type` | enum | 任务类型 |
| `status` | enum | 任务状态 |
| `priority` | int | 优先级 |
| `requested_by` | string | 发起用户或系统 |
| `request_payload` | json | 请求参数 |
| `baseline_artifact_id` | string nullable | 基线 artifact |
| `result_summary` | json nullable | 结果摘要 |
| `error_code` | string nullable | 错误码 |
| `error_message` | text nullable | 错误信息 |
| `created_at` | datetime | 创建时间 |
| `started_at` | datetime nullable | 开始时间 |
| `finished_at` | datetime nullable | 结束时间 |

状态机：

```text
pending -> queued -> running -> succeeded
pending -> queued -> running -> failed
pending -> queued -> running -> cancelled
failed -> retrying -> queued
```

规则：

- `Task` 是业务对象。
- `TaskRun` 是实际执行对象。
- 一个 task 可以对应多个 task run。

### 8.4 TaskRun

含义：某个 task 的一次实际执行记录。

建议字段：

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `id` | string | task run 唯一 ID |
| `task_id` | string | 所属 task |
| `attempt` | int | 第几次尝试 |
| `worker_name` | string | worker 名称 |
| `workflow_name` | string nullable | 使用的 workflow |
| `workflow_run_id` | string nullable | workflow 内部运行 ID |
| `checkpoint_thread_id` | string nullable | checkpoint thread |
| `status` | enum | 执行状态 |
| `started_at` | datetime | 开始时间 |
| `finished_at` | datetime nullable | 结束时间 |

### 8.5 TaskEvent

含义：任务执行过程中的标准事件流。

建议字段：

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `id` | string | event 唯一 ID |
| `task_id` | string | 所属 task |
| `task_run_id` | string nullable | 所属 task run |
| `session_id` | string | 所属 session |
| `branch_id` | string | 所属 branch |
| `scene_id` | string nullable | 关联 scene |
| `event_type` | string | 标准事件类型 |
| `event_level` | enum | `debug/info/warn/error` |
| `node_key` | string nullable | workflow 节点 |
| `payload` | json | 事件负载 |
| `created_at` | datetime | 事件时间 |

标准事件类型初版：

- `task.created`
- `task.queued`
- `task.started`
- `task.progress`
- `workflow.node_started`
- `workflow.node_completed`
- `artifact.published`
- `validation.started`
- `validation.failed`
- `validation.passed`
- `repair.started`
- `repair.applied`
- `repair.failed`
- `render.started`
- `render.completed`
- `task.completed`
- `task.failed`
- `task.cancelled`

### 8.6 Artifact

含义：每个阶段可被消费、编辑、对比、回退的结构化结果。

artifact 类型初版：

- `source_document`
- `script`
- `storyboard`
- `visual_strategy`
- `scene_intent_bundle`
- `scene_layout_bundle`
- `scene_code_bundle`
- `validation_report`
- `repair_report`
- `preview_image`
- `preview_video`
- `rendered_video`

建议字段：

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `id` | string | artifact 唯一 ID |
| `session_id` | string | 所属 session |
| `branch_id` | string | 所属 branch |
| `task_id` | string | 产出任务 |
| `artifact_type` | enum | 产物类型 |
| `artifact_subtype` | string nullable | 子类型 |
| `version` | int | 版本 |
| `content_json` | json nullable | 结构化内容 |
| `content_text` | text nullable | 文本内容 |
| `storage_url` | string nullable | 大文件地址 |
| `summary` | text nullable | 摘要 |
| `parent_artifact_id` | string nullable | 父产物 |
| `created_at` | datetime | 创建时间 |

规则：

- artifact 是产品事实来源。
- repair 后必须创建新 artifact，不能直接覆盖旧 artifact。
- 大文件走对象存储，数据库只保存元数据和地址。

### 8.7 SceneArtifact

含义：scene 级别独立可编辑、可重生成、可校验的产物。

建议字段：

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `id` | string | scene artifact 唯一 ID |
| `artifact_id` | string | 所属 bundle artifact |
| `session_id` | string | 所属 session |
| `branch_id` | string | 所属 branch |
| `scene_id` | string | 业务 scene ID |
| `scene_order` | int | 顺序 |
| `scene_type` | enum | scene 类型 |
| `script_text` | text | scene 口播或文案 |
| `visual_intent` | json nullable | 视觉意图 |
| `layout_spec` | json nullable | 几何布局 |
| `code_text` | text nullable | Remotion 代码 |
| `validation_report` | json nullable | 校验报告 |
| `preview_image_url` | string nullable | 预览图 |
| `status` | enum | scene 状态 |
| `version` | int | scene 版本 |
| `created_at` | datetime | 创建时间 |

## 9. 生成链路需求

目标链路：

```text
Source Ingest
-> Script Rewrite
-> Storyboard Planning
-> Style Routing
-> Scene Intent Generation
-> Constraint-based Layout Solve
-> Code Generation from Primitives
-> Static Validation
-> Preview Render
-> Visual Validation
-> Repair / Retry
-> Artifact Publish
```

### 9.1 Source Ingest

输入：

- `source_type`
- `source_content`
- `user_preference` 可选

输出：

- `source_document` artifact。

验收：

- 原始输入不可丢失。
- 输入和后续 session 可追溯。

### 9.2 Script Rewrite

职责：

- 将原文改写为适合视频讲述的口播脚本。
- 不负责分镜、布局和具体视觉表达。

输出：

- `script` artifact。

验收：

- 输出结构化保存。
- 记录使用的 prompt version、model role 和 task id。

### 9.3 Storyboard Planning

职责：

- 将脚本拆分为 scene。
- 生成每个 scene 的叙事目标、信息密度、推荐时长和内容类型。

输出：

- `storyboard` artifact。

验收：

- 每个 scene 有稳定 `scene_id`。
- 每个 scene 有 `scene_order`、`narrative_goal`、`script_text`、`duration_hint`、`information_density`。

### 9.4 Style Routing

职责：

- 根据内容类型、用户偏好和 storyboard 决定视觉风格族。

可选风格族初版：

- `editorial_typography`
- `product_ui`
- `cinematic_explainer`
- `collage_mixed_media`
- `brutal_poster`
- `diagrammatic_minimal`

输出：

- `visual_strategy` artifact，包含 `style_family`、`theme_profile`、`motion_profile`、`asset_policy`、`scene_type_mapping`。

验收：

- 不同 scene type 可以映射不同 primitive 组合。
- 视觉策略可落库、可复用、可被代码生成阶段消费。

### 9.5 Scene Intent Generation

职责：

- 为每个 scene 输出设计意图，而不是最终坐标。

输出字段建议：

- `scene_id`
- `scene_type`
- `visual_goal`
- `primitive_candidates`
- `information_hierarchy`
- `reveal_order`
- `asset_needs`
- `preferred_regions`

验收：

- 不输出最终绝对坐标作为权威布局。
- 每个 primitive 都有 role 和 importance。

### 9.6 Constraint-based Layout Solve

职责：

- 程序根据 scene intent、文字长度、画布尺寸、安全区和 primitive 约束求解 layout。

输出：

- `layout_spec`，包含 `x`、`y`、`width`、`height`、`padding`、`font_size`、`line_height`、`z_index` 等字段。

验收：

- 布局结果必须通过静态几何校验。
- 文本高度估算必须独立执行。
- 旋转、阴影等视觉效果需要计入 bbox 扩张。

### 9.7 Code Generation from Primitives

职责：

- 将受控 primitive、layout spec、theme profile、motion profile 转为 Remotion 代码。

验收：

- coder 不再从零自由生成所有结构。
- 代码必须引用或模拟标准 primitive。
- 输出必须包含 scene id、可渲染组件和必要 props。

### 9.8 Static Validation

职责：

- 对 schema、布局、文本、层级、时序和代码结构做程序级检查。

验收：

- 输出 `validation_report` artifact。
- 校验失败必须包含 `error_code`、`severity`、`scene_id`、`target_path`、`message`、`repair_hint`。

### 9.9 Preview Render

职责：

- 渲染 scene 首帧、关键帧或低清预览。

验收：

- 渲染结果保存为 artifact。
- 渲染失败可重试并记录 event。

### 9.10 Visual Validation

职责：

- 基于截图和规则检查可读性、视觉重心、空洞程度、拥挤程度和廉价图标化倾向。

验收：

- 输出视觉验收报告。
- 初版可采用规则和人工可读报告，后续接入视觉模型。

### 9.11 Repair / Retry

repair 优先级：

1. 纯布局修复。
2. 文本拆分与容器调参。
3. primitive 替换。
4. scene intent 局部重生成。
5. 整个 scene 重生成。

验收：

- 每次 repair 都必须写 event 和 artifact。
- repair 不直接覆盖原始 artifact。
- repair 达到最大次数后任务失败，并给出可读原因。

## 10. 布局与校验需求

### 10.1 布局求解器必须处理

- 1080x1920 画布边界。
- safe area。
- 文本行数和容器高度。
- 最小字号。
- 卡片最小尺寸。
- 旋转后的 bbox 扩张。
- 阴影、描边、发光等额外占位。
- 元素最小间距。
- zIndex 与 reveal order 对齐。
- 视觉平衡和信息密度。

### 10.2 文本溢出校验

检查项：

- 根据 `font_size`、`line_height`、`width` 估算换行。
- 检查文本容器高度是否足够。
- 检查是否超过最多行数。
- 检查中英文混排、长英文 token、URL、数字串。

repair 策略：

- 扩大容器。
- 降低字号但不能低于最小字号。
- 拆成多卡。
- 拆成多 beat scene。
- 回到 scene intent 重新布局。

### 10.3 几何校验

检查项：

- safe area。
- bbox 越界。
- 旋转 bbox 越界。
- 元素碰撞。
- 关键内容遮挡。
- 层级冲突。

### 10.4 结构校验

检查项：

- schema 完整性。
- scene id 唯一性。
- primitive 是否受支持。
- required props 是否齐全。
- marks 是否合法。
- 动效引用是否存在。

## 11. 视觉系统需求

### 11.1 Theme Profile

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

验收：

- theme profile 可被 layout、codegen 和 render 阶段消费。
- theme profile 不直接写死在 prompt 中。

### 11.2 Primitive 库

首批 primitive：

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

规则：

- 线条和 icon 只能作为辅助，不应主导画面。
- 大字排版、截图、图像、图表、强块面应成为主表达。
- primitive 必须定义输入 schema、布局约束和渲染约束。

### 11.3 Scene Type

初始 scene type：

- `statement`
- `contrast`
- `process`
- `timeline`
- `data_point`
- `product_demo`
- `quote`
- `emotion_peak`

验收：

- scene planner 必须输出 scene type。
- style router 基于 scene type 选择 primitive 组合。
- 不同 scene type 不应全部收敛到同一类 LogicCard。

## 12. API 需求

### 12.1 Session API

#### `POST /api/sessions`

用途：创建 session。

请求：

```json
{
  "source_type": "text",
  "source_content": "文章内容",
  "title": "可选标题",
  "user_preference": {}
}
```

响应：

```json
{
  "session_id": "sess_xxx",
  "branch_id": "br_xxx",
  "status": "active"
}
```

#### `GET /api/sessions/{session_id}`

用途：查询 session 概览。

#### `GET /api/sessions/{session_id}/branches`

用途：查询 session 下分支。

#### `GET /api/sessions/{session_id}/timeline`

用途：查询 session 时间线。

### 12.2 Task API

#### `POST /api/sessions/{session_id}/tasks`

用途：创建任务。

请求：

```json
{
  "branch_id": "br_xxx",
  "task_type": "create_video",
  "request_payload": {},
  "baseline_artifact_id": null
}
```

响应：

```json
{
  "task_id": "task_xxx",
  "status": "queued"
}
```

#### `GET /api/tasks/{task_id}`

用途：查询任务状态。

#### `GET /api/tasks/{task_id}/events`

用途：查询任务事件。

#### `GET /api/tasks/{task_id}/events_sse`

用途：订阅任务事件流。

#### `POST /api/tasks/{task_id}/cancel`

用途：取消任务。

#### `POST /api/tasks/{task_id}/retry`

用途：重试任务。

### 12.3 Artifact API

#### `GET /api/artifacts/{artifact_id}`

用途：查询 artifact 详情。

#### `GET /api/scene-artifacts/{scene_artifact_id}`

用途：查询 scene artifact 详情。

#### `POST /api/artifacts/{artifact_id}/branch`

用途：从 artifact 创建 branch。

请求：

```json
{
  "name": "从视觉策略 v2 分支",
  "reason": "尝试另一种风格"
}
```

#### `GET /api/branches/{branch_id}/artifacts`

用途：查询 branch 下 artifact 历史。

### 12.4 与现有 API 的兼容策略

短期保留现有 API：

- `/api/generate_script_sse`
- `/api/generate_animation_sse`
- `/api/workflows/{workflow_name}/history`
- `/api/workflows/{workflow_name}/replay_sse`
- `/api/workflows/{workflow_name}/fork_sse`
- `/api/workflows/animation/regenerate_scene_sse`

迁移策略：

- 新 API 写入 session、task、artifact。
- 旧 API 可作为兼容层调用新 task system。
- 前端逐步从 workflow history 切换到 session timeline。
- checkpoint history 不再作为产品主历史暴露。

## 13. 任务系统需求

### 13.1 队列能力

任务系统需要支持：

- 异步执行。
- 任务优先级。
- 任务取消。
- 失败重试。
- worker 异常恢复。
- 按任务类型限制并发。
- 按 session 或 branch 控制冲突。

### 13.2 执行模型

```text
API 创建 task
-> task 入库
-> task 进入队列
-> worker 拉取 task
-> 创建 task_run
-> WorkflowRunner 启动 LangGraph 或 pipeline
-> 每个阶段写 TaskEvent 和 Artifact
-> 完成后更新 task 状态
```

### 13.3 LangGraph 定位

LangGraph 继续负责单任务内部 agent 编排，例如：

- script rewrite 内部循环。
- storyboard planning 内部推理。
- scene generation agent 协作。
- repair pipeline 局部编排。

LangGraph 不负责：

- 产品级历史。
- 权限模型。
- 多任务调度。
- artifact 主存储。
- 跨 session 查询。

## 14. 数据与存储需求

### 14.1 主数据库

推荐 PostgreSQL。

最小表集合：

- `users`
- `sessions`
- `branches`
- `tasks`
- `task_runs`
- `task_events`
- `artifacts`
- `scene_artifacts`
- `render_jobs`

增强表：

- `task_locks`
- `prompt_profiles`
- `theme_profiles`
- `asset_references`
- `quality_scores`
- `usage_metrics`

### 14.2 缓存

短期热缓存推荐 Redis，长期可复用结果必须进入 artifact。

cache key 至少包含：

- `model_role`
- `prompt_version`
- `session_id`
- `branch_id`
- `scene_id`
- `input_hash`

不建议只放缓存的内容：

- scene code。
- validation report。
- preview image。
- repair result。

### 14.3 对象存储

以下内容应使用对象存储或本地对象存储抽象：

- preview image。
- preview video。
- rendered video。
- 大型截图。
- 素材文件。

数据库只保存 `storage_url`、hash、size、mime type、metadata。

## 15. 并发与一致性需求

### 15.1 隔离原则

- session 之间天然隔离。
- branch 之间逻辑隔离。
- task 之间可并发，但写入同一 branch 或 scene 时需要冲突控制。

### 15.2 冲突场景

- 同一 scene 被两个 regenerate task 同时修改。
- 同一 branch 被多个任务同时写 head artifact。
- 用户创建 branch 时原任务仍在运行。
- repair 任务基于过期 artifact 继续写入。

### 15.3 控制策略

- branch 使用乐观锁版本号。
- scene 写入使用 scene 级锁或唯一 active task 限制。
- task 创建时记录 `baseline_artifact_id`。
- artifact 发布时校验 baseline 是否过期。
- 冲突时任务进入 `failed` 或 `blocked`，并输出可读错误。

## 16. 可观测性需求

### 16.1 日志

每条关键日志至少包含：

- `session_id`
- `branch_id`
- `task_id`
- `task_run_id`
- `scene_id`
- `node_key`
- `artifact_id`

### 16.2 指标

需要统计：

- 每类 task 成功率。
- 每类 scene 失败率。
- validator 失败率。
- repair 触发率。
- repair 成功率。
- overflow 命中率。
- 风格族分布。
- 平均生成时长。
- 平均 render 时长。
- 队列等待时长。

### 16.3 调试面板

后续可提供内部调试视图：

- session timeline。
- task event 列表。
- artifact diff。
- scene validation report。
- repair 前后对比。

## 17. 安全与权限需求

本期可做基础隔离，不要求完整商业化权限。

最低要求：

- 每个 session 记录 `user_id`。
- 查询 session、task、artifact 时校验归属。
- task event 不泄露其他用户 payload。
- 对象存储 URL 不应长期裸露公共访问地址。

## 18. 验收标准

### 18.1 功能验收

- 可以创建 session，并返回 session 和 branch。
- 可以创建 create_video task，并通过事件流看到进度。
- 每个生成阶段至少有一个 artifact 或 event 记录。
- 可以查询 session timeline。
- 可以从 artifact 创建 branch。
- 可以对单 scene 发起 regenerate task。
- validator 可以输出结构化 validation report。
- repair 可以生成新 artifact，并保留旧 artifact。

### 18.2 质量验收

- 文本溢出和元素越界可以被 validator 检测。
- repair 结果可统计成功或失败。
- style router 能输出至少 3 种 style family。
- primitive 库至少支持 6 个可用 primitive。
- scene type 至少覆盖 `statement`、`contrast`、`process`、`data_point`。

### 18.3 工程验收

- 不再依赖 `InMemorySaver` 作为产品历史事实来源。
- checkpoint 只用于 workflow 恢复。
- 标准 event 能驱动前端进度展示。
- task 状态机可测试。
- artifact 与 task、session、branch 的关系可追溯。

## 19. 里程碑

### M1 稳定性底座

目标：不大改产品形态，先解决溢出、校验和不可追踪问题。

交付：

- scene artifact 初版。
- layout validator 初版。
- text overflow validator 初版。
- repair 初版。
- 标准 task event 抽象。
- cache key 增加 prompt version。
- 统一 UTF-8 编码。

验收：

- 单 scene 可以生成 validation report。
- repair 前后结果可追踪。
- 前端能看到标准进度事件。

### M2 业务主模型

目标：从 checkpoint 驱动转向产品对象驱动。

交付：

- PostgreSQL 表结构。
- session / branch / task / artifact repository。
- timeline API。
- branch API。
- task 查询、取消、重试 API。
- checkpoint 降级为内部恢复层。

验收：

- 可查询 session timeline。
- 可从 artifact 创建 branch。
- 可对 task 做状态查询和重试。

### M3 视觉系统

目标：解决视觉风格单一和 UI 质感偏低的问题。

交付：

- style router。
- theme profile。
- primitive 库初版。
- scene type 路由。
- coder 改为基于 primitive 生成。

验收：

- 至少支持 3 种 style family。
- 至少支持 6 个 primitive。
- 同一脚本不同 scene type 有不同 primitive 组合。

### M4 渲染与视觉验收闭环

目标：让系统从“会生成”进化到“会自检”。

交付：

- preview render worker。
- 首帧或关键帧截图 artifact。
- visual validation report。
- repair 与 retry 策略联动。

验收：

- scene 生成后可得到预览图。
- 预览图可进入视觉验收。
- 视觉验收失败可触发 repair 或 retry。

## 20. 风险与应对

| 风险 | 影响 | 应对 |
| --- | --- | --- |
| 重构跨度过大 | 交付周期变长 | 分四期推进，先保留现有 workflow |
| validator 过严 | 生成成功率下降 | 分级校验，先 warn 后 block |
| repair 复杂度过高 | 开发成本上升 | 先做低成本布局修复，再逐步扩展 |
| 视觉系统不稳定 | 输出风格漂移 | theme profile 和 primitive schema 固化边界 |
| 多任务冲突 | 数据不一致 | baseline artifact、branch 乐观锁、scene 写锁 |
| 渲染 worker 不稳定 | 验收闭环阻塞 | 渲染独立任务化，失败可重试 |

## 21. 开放问题

需要后续确认：

1. 任务队列选型使用 Celery、RQ，还是 PostgreSQL 自建 worker。
2. preview render worker 是否和 generation worker 分离部署。
3. visual validation 初版使用纯规则、规则加视觉模型，还是人工可读报告。
4. 首批 primitive 是否需要直接适配现有前端预览组件。
5. artifact diff 的前端展示粒度是 scene、layout，还是 code。
6. branch 冲突是否对用户展示为“需要刷新基线”还是自动创建新 branch。
7. 用户体系短期是否使用匿名 user id，还是接入真实账号系统。

## 22. 推荐优先级

如果只能先做三件事，建议顺序如下：

1. 布局 validator + repair。
2. session / task / artifact 数据模型。
3. style router + primitive 库。

原因：

- 第一步解决结果稳定性。
- 第二步解决产品可用性和回溯能力。
- 第三步解决视觉上限。

## 23. 最终定义

本 PRD 定义的不是一次简单代码重构，而是一次后端产品能力升级。

升级后的后端应从：

- workflow 为中心。
- checkpoint 为历史。
- prompt 为约束。
- coder 自由生成所有视觉结构。

转向：

- session 为创作上下文。
- task 为执行单位。
- artifact 为事实来源。
- scene artifact 为局部编辑单元。
- layout solver 和 validator 为稳定性保障。
- style router 和 primitive 库为视觉上限保障。
- repair 与 render validation 为质量闭环。

完成这次升级后，当前的溢出、视觉单一和回溯不可用问题，才能从“不断补 prompt”的临时方案，进入可持续演进的系统方案。
