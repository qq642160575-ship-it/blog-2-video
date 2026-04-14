# Video-Back 后端架构说明

## 项目结构

```
video-back/
├── api/                    # API 路由和 schemas
│   ├── routes.py          # 所有 API 端点
│   └── schemas.py         # 请求/响应模型
├── app/                    # 应用配置和依赖
│   ├── config.py          # 配置管理
│   ├── dependencies.py    # 依赖注入容器
│   └── errors.py          # 错误定义
├── domain/                 # 领域模型
│   ├── common/            # 通用枚举和 ID 生成
│   ├── sessions/          # Session 实体和服务
│   ├── tasks/             # Task 实体和状态机
│   └── artifacts/         # Artifact 实体和服务
├── orchestration/          # 任务编排
│   ├── task_dispatcher.py # 任务分发器
│   ├── task_runner.py     # 任务执行器
│   ├── workflow_runner.py # LangGraph 适配器
│   └── event_publisher.py # 事件发布器
├── pipelines/              # 业务流程
│   ├── base.py            # Pipeline 基类
│   └── create_video.py    # 创建视频流程
├── generation/             # 生成模块
│   ├── style_router/      # 视觉风格路由
│   ├── scene_intent/      # 场景意图生成
│   └── storyboard/        # 故事板规划
├── layout/                 # 布局系统
│   ├── schemas.py         # 布局数据结构
│   ├── primitives.py      # 原语定义
│   ├── solver.py          # 布局求解器
│   ├── validator.py       # 布局验证器
│   ├── repair.py          # 布局修复器
│   └── text_metrics.py    # 文本度量
├── persistence/            # 持久化层
│   ├── db.py              # 数据库连接
│   ├── models.py          # SQLAlchemy 模型
│   ├── repositories.py    # 数据访问层
│   └── migrations/        # 数据库迁移
├── infra/                  # 基础设施
│   └── queue/             # 队列实现
├── workers/                # 后台工作进程
│   └── task_worker.py     # 任务工作器
└── workflow/               # 旧的 LangGraph workflow (兼容)
    └── animation_work_flow.py

```

## 核心概念

### 1. Session (会话)
- 代表一个创作上下文
- 包含源文档、用户偏好等
- 可以有多个 Branch

### 2. Branch (分支)
- 代表一个版本分支
- 每个 Branch 有独立的 artifact 版本链
- 支持从任意 artifact 创建新分支

### 3. Task (任务)
- 代表一个异步执行单元
- 有明确的状态机: pending -> queued -> running -> succeeded/failed
- 产生 events 和 artifacts

### 4. Artifact (产物)
- 代表生成的结果
- 有版本号,可追溯
- 类型包括: script, storyboard, visual_strategy, scene_code_bundle 等

### 5. Scene Artifact (场景产物)
- Scene 级别的可编辑单元
- 包含 script, visual_intent, layout_spec, code 等
- 支持独立版本和重新生成

## API 端点

### Session API
- `POST /api/sessions` - 创建会话
- `GET /api/sessions/{session_id}` - 获取会话信息
- `GET /api/sessions/{session_id}/timeline` - 获取时间线

### Task API
- `POST /api/sessions/{session_id}/tasks` - 创建任务
- `GET /api/tasks/{task_id}` - 获取任务状态
- `GET /api/tasks/{task_id}/events` - 获取任务事件
- `GET /api/tasks/{task_id}/events_sse` - SSE 流式事件
- `POST /api/tasks/{task_id}/cancel` - 取消任务
- `POST /api/tasks/{task_id}/retry` - 重试任务

### Artifact API
- `GET /api/artifacts/{artifact_id}` - 获取产物
- `GET /api/scene-artifacts/{scene_artifact_id}` - 获取场景产物
- `GET /api/branches/{branch_id}/artifacts` - 列出分支产物
- `POST /api/artifacts/{artifact_id}/branch` - 从产物创建分支

### 兼容旧 API
- `POST /api/generate_animation_sse` - 生成动画 (兼容)
- `GET /api/workflows/{workflow_name}/history` - 工作流历史
- `POST /api/workflows/{workflow_name}/replay_sse` - 重放工作流
- `POST /api/workflows/animation/regenerate_scene_sse` - 重新生成场景

## 开发指南

### 启动应用

```bash
# 激活虚拟环境
source .venv/bin/activate

# 运行应用
python main.py
```

### 运行测试

```bash
source .venv/bin/activate
pytest tests/ -v
```

### 数据库迁移

```bash
# 创建所有表
python -m persistence.migrations.init_db create

# 删除所有表
python -m persistence.migrations.init_db drop
```

## 配置

配置通过 `.env` 文件或环境变量设置:

```env
DATABASE_URL=sqlite+aiosqlite:///./dev.db
REDIS_URL=redis://localhost:6379
OBJECT_STORAGE_ROOT=.cache/artifacts
QUEUE_BACKEND=inline
PROMPT_VERSION=v1
CANVAS_WIDTH=1080
CANVAS_HEIGHT=1920
LOG_LEVEL=INFO
```

## 架构设计原则

1. **Session 是创作上下文** - 所有操作都在 session 下进行
2. **Task 是执行单元** - 异步任务通过队列执行
3. **Artifact 是事实来源** - 所有生成结果都保存为 artifact
4. **Event 是进度来源** - 前端通过 event 获取进度和调试信息
5. **Layout 保证稳定性** - validator + repair 确保画面正确性
6. **Style Router 保证质量** - 结构化的视觉策略和原语库

## 下一步开发

根据 `doc/backend-detailed-design.md`:

- **M1**: 已完成 - 稳定性底座 (validator, repair, event)
- **M2**: 已完成 - 业务主模型 (session, task, artifact)
- **M3**: 部分完成 - 视觉系统 (style_router, primitives, solver)
- **M4**: 待实现 - 渲染验收闭环 (preview_renderer, visual_validator)

## 注意事项

1. 当前使用内存存储,生产环境需要切换到 PostgreSQL
2. 队列使用 InlineQueue,生产环境建议使用 Redis Queue
3. 对象存储当前使用本地文件系统,生产环境建议使用 S3/MinIO
4. LangGraph workflow 通过 WorkflowRunner 适配,逐步迁移到新架构
