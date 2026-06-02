# AIH Infra Open WebUI

基于 Open WebUI 的 AIH-Infra 特化分支，重点面向研究型知识库、可追溯引用、可控 Agent RAG 和知识库版本一致性。

这个仓库适合以下场景：

- 需要在 Open WebUI 基础上做知识库增强与研究工作流探索
- 希望保留上游的模型接入与通用聊天能力
- 需要更强的 RAG 参数控制、chunk 巡检、引用回溯与 Agent 边界治理

## 项目定位

相对于上游 Open WebUI，这个分支更偏向“研究型知识库工作台”，而不是纯通用聊天平台。

当前已经集成或强化的方向包括：

- 知识库级切块参数配置
- 聊天侧 RAG 参数面板
- Agent / Traditional / Disabled 三态知识检索模式
- Agent scope、工具检索边界与部分工具门控
- 知识库文件快照、stale 检测与刷新
- chunk 巡检、统计、引用增强与部分页码追踪能力

这个分支聚焦研究型知识库工作流，公开版仓库默认以代码和运行方式为主，不再保留内部设计文档。

## 技术栈

- 前端：SvelteKit + TypeScript
- 后端：FastAPI
- 数据层：SQLite / PostgreSQL 等
- 运行方式：本地开发、Docker、Docker Compose

## 快速开始

### 1. 环境要求

- Node.js `18` 到 `22`
- npm `>= 6`
- Python `3.11` 或 `3.12`
- 建议使用 `uv` 或虚拟环境管理 Python 依赖

### 2. 安装前端依赖

```bash
npm install
```

### 3. 安装后端依赖

```bash
pip install -r backend/requirements.txt
```

或使用项目元数据安装：

```bash
pip install -e .
```

### 4. 配置环境变量

复制环境模板并按需修改：

```bash
cp .env.example .env
```

Windows PowerShell 可用：

```powershell
Copy-Item .env.example .env
```

最常用配置：

- `OLLAMA_BASE_URL`
- `OPENAI_API_BASE_URL`
- `OPENAI_API_KEY`
- `CORS_ALLOW_ORIGIN`

## 本地开发

### 前端开发

```bash
npm run dev
```

### 前端类型检查

```bash
npm run check
```

### 前端测试

```bash
npm run test:frontend
```

### 后端启动

Linux / macOS:

```bash
bash backend/start.sh
```

Windows:

```powershell
.\backend\start_windows.bat
```

如果你已经用 `pip install -e .` 安装了项目，也可以直接运行：

```bash
open-webui serve
```

## Docker

### 构建镜像

```bash
docker build -t aih-infra-open-webui:local .
```

### 使用 Compose 启动

```bash
docker compose up --build
```

默认 Compose 配置位于 [docker-compose.yaml](./docker-compose.yaml)。

## 仓库结构

```text
backend/    FastAPI 后端与数据模型
src/        SvelteKit 前端
static/     静态资源
docs/       补充文档
scripts/    构建与辅助脚本
test/       测试资源
```

## 发布到 GitHub 前的建议

- 不要提交 `.env`、数据库文件、`node_modules`、构建产物和个人工作副本
- 首次公开前建议新建一个干净分支，专门用于发布整理
- 推送前执行一次 `git status`，确认没有把本地调试数据带上去

## 与上游关系

本仓库是基于 Open WebUI 的特化分支，不是上游官方仓库。若需了解上游能力、官方文档或社区资源，请参考 Open WebUI 官方项目。

## License

本项目保留仓库内现有许可证与历史许可证文件：

- [LICENSE](./LICENSE)
- [LICENSE_HISTORY](./LICENSE_HISTORY)
- [LICENSE_NOTICE](./LICENSE_NOTICE)
