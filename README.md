# blog-2-video

一个把博客/口播原稿整理成视频脚本，并在 IDE 中预览、编辑动画场景代码的实验性项目。

当前仓库由两个子项目组成：

- `video-back`：Python + FastAPI + LangGraph 后端，负责把原始文本重写成更适合口播的视频脚本，并通过 SSE 流式返回中间结果。
- `wms-video-ide`：Vite + React + Remotion 前端，提供三栏式 IDE，用来输入原文、查看时间轴、预览视频以及编辑场景代码。

## 项目现状

这个仓库目前更接近一个「脚本重写 + 视频 IDE 原型」：

- 已完成：原始文本 -> 流式生成/迭代优化口播稿。
- 已完成：前端展示改写日志、预览 Remotion 视频、编辑场景代码、调整时间轴。
- 未完成：口播稿 -> Director / Architect / Coder 全链路生成视频场景代码。前端第二步按钮目前还是占位逻辑。
- 当前预览内容主要来自前端内置的 `MOCK_SCENES`，适合演示编辑器与播放器联动，不代表完整生产链路已经打通。

如果你希望先跑通一个可演示版本，这个仓库已经够用；如果你希望一键从文章直接产出完整视频，还需要继续补后端生成链路。

## 核心能力

### 1. 文本重写工作流

后端暴露 `POST /api/generate_script_sse`：

- 输入原始文本 `source_text`
- 启动 LangGraph 工作流
- 由内容生成/评审节点循环优化脚本
- 通过 SSE 持续推送 `setup`、`updates`、`end` 事件

当前工作流包含：

- `content_writer`
- `content_reviewer`
- 基于评分阈值的循环迭代

默认逻辑：

- 最多迭代 3 轮
- 评分阈值 80 分

### 2. 视频 IDE

前端界面分为三列：

- 左侧：原始文本输入、脚本生成入口、时间轴、脚本面板
- 中间：Remotion Player 实时预览
- 右侧：Monaco Editor 编辑场景代码 + 执行日志面板

当前 IDE 支持：

- 输入原始文本并调用后端流式生成脚本
- 展示每一轮工作流日志与评分反馈
- 在 Remotion Player 中实时预览场景
- 在 Monaco 中直接修改场景代码
- 根据选中场景同步预览位置

## 技术栈

### 前端

- React 19
- TypeScript
- Vite
- Remotion / `@remotion/player`
- Monaco Editor
- Zustand
- Tailwind CSS

### 后端

- Python
- FastAPI
- LangGraph
- LangChain
- Anthropic 模型接入
- Pydantic
- PyYAML

## 目录结构

```text
blog-2-video/
├─ video-back/         # FastAPI + LangGraph 后端
│  ├─ agents/          # 多个角色 agent 定义
│  ├─ models/          # 模型初始化
│  ├─ prompts/         # YAML Prompt 与 PromptManager
│  ├─ workflow/        # LangGraph 工作流
│  └─ main.py          # FastAPI 入口
├─ wms-video-ide/      # React + Remotion IDE
│  ├─ src/components/  # 左侧面板、播放器、编辑器等
│  ├─ src/store/       # Zustand 状态管理
│  └─ vite.config.ts   # 本地开发代理到 8000 端口
└─ README.md
```

## 快速开始

建议本地准备：

- Node.js 20+
- npm 10+
- Python 3.11 或 3.12

### 1. 启动后端

进入后端目录：

```bash
cd video-back
```

创建并激活虚拟环境：

```bash
python -m venv .venv
```

Windows PowerShell:

```bash
.venv\Scripts\Activate.ps1
```

macOS / Linux:

```bash
source .venv/bin/activate
```

安装依赖。

仓库当前没有提供 `requirements.txt`，下面是根据代码导入整理出的最小运行依赖：

```bash
pip install fastapi uvicorn pydantic langgraph langchain-core langchain-anthropic python-dotenv pyyaml
```

配置环境变量 `video-back/.env`：

```env
ANTHROPIC_API_KEY=your_key
ANTHROPIC_BASE_URL=your_base_url
```

启动服务：

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

启动后接口地址为：

```text
http://localhost:8000
```

### 2. 启动前端

另开一个终端，进入前端目录：

```bash
cd wms-video-ide
```

安装依赖：

```bash
npm install
```

启动开发服务器：

```bash
npm run dev
```

默认访问：

```text
http://localhost:5173
```

前端已经在 [`wms-video-ide/vite.config.ts`](./wms-video-ide/vite.config.ts) 中把 `/api` 代理到 `http://localhost:8000`，本地联调时不需要额外改接口地址。

## 使用流程

1. 在左侧输入你的博客正文、提纲或口播草稿。
2. 点击第一步按钮，让后端流式生成更适合视频表达的脚本。
3. 在右侧日志里查看每一轮生成、评分和反馈。
4. 在中间播放器查看当前 Remotion 场景效果。
5. 在右侧编辑器里直接修改场景代码，观察预览变化。

## API 说明

### `POST /api/generate_script_sse`

请求体：

```json
{
  "source_text": "你的原始文本"
}
```

返回类型：

```text
text/event-stream
```

事件示例：

```text
data: {"type":"setup","message":"Workflow Initialized"}

data: {"type":"updates","data":{...}}

data: {"type":"end","message":"Workflow Compeleted"}
```

## 关键实现说明

### 后端

- `video-back/main.py`：FastAPI 入口，提供 SSE 接口。
- `video-back/workflow/conversational_tone_work_flow.py`：当前主要工作流，负责脚本重写和评分循环。
- `video-back/prompts/`：各角色 Prompt 配置，使用 YAML 管理。
- `video-back/models/get_model.py`：当前通过 `ChatAnthropic` 初始化模型。

### 前端

- `wms-video-ide/src/components/LeftPanel/SourceInput.tsx`：发起 SSE 请求并解析流式结果。
- `wms-video-ide/src/components/PreviewPlayer/`：承载 Remotion Player。
- `wms-video-ide/src/components/CodeEditor/`：Monaco 编辑器和执行日志。
- `wms-video-ide/src/store/useIdeStore.ts`：核心状态管理，包含当前内置场景数据。

## 已知限制

- 第二阶段“根据口播稿生成 Timeline / 视频场景”的逻辑还没有真正接到后端。
- 前端目前主要依赖内置场景数据做演示。
- 仓库暂未提供后端依赖锁定文件，首次部署需要手动安装 Python 依赖。
- 默认模型接入为 Anthropic；如果要切换到其他供应商，需要调整 `video-back/models/get_model.py`。

## 后续建议

比较自然的下一步有三件事：

- 把前端第二步按钮真正接到 `Director -> Architect -> Coder` 工作流
- 为后端补上 `requirements.txt` 或 `pyproject.toml`
- 增加场景生成、代码执行和渲染输出的端到端接口

## 适用场景

这个项目适合拿来做：

- 博客转短视频原型
- AI 辅助动画脚本 IDE
- LangGraph 多 Agent 工作流实验
- Remotion 场景生成与可视化编辑演示

如果你要把它继续产品化，建议优先补齐场景自动生成、渲染导出、依赖管理和异常处理。
