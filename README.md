# Open WebUI AIH-Infra

> 面向人文学科研究的 RAG 增强平台 —— 基于 [Open WebUI](https://github.com/open-webui/open-webui) 的特化分支

**AIH-Infra**（AI Humanities Infrastructure）是人文学科 AI 基础设施项目的检索层实现。通过对 Open WebUI 的定向改造，为人文学者提供**可追溯、可调控、可视化**的 RAG 检索能力。

本项目是 [人文学科AI基础设施白皮书](./人文学科AI基础设施白皮书v2.md) 中"朴素 RAG 毕业方案"的工程实现。

---

## 核心理念

**每一条系统输出，都必须能够返回原书的那一页。**

商业知识库产品（NotebookLLM、Sider 等）将 RAG 管线封装为黑箱，研究者无法知道系统检索了什么、遗漏了什么。AIH-Infra 将 RAG 全链路透明化，使学术研究的可追溯性得到技术保障。

---

## 改造特性

### 1. 知识库级 RAG 自定义

不同文献需要不同的切块策略。古籍校注本与现代学术专著的最优参数截然不同。

- 每个知识库独立配置：切块大小、重叠区间、切块方式、Markdown 标题切块开关
- 三层参数优先级：`会话级 > 知识库级 > 全局管理员配置`
- 所有新字段 nullable，完全向后兼容

### 2. 会话级 RAG 参数调控

研究者可在对话中实时调整检索参数，无需修改全局配置：

- **Top-K**：单知识库检索数量
- **Global Top-K**：跨知识库全局排序 vs 按来源分别返回
- **Relevance Threshold**：相关度阈值，过滤低质量结果

### 3. Markdown 标题切块优化

原版存在重复切块和碎片块问题。改造后实现三步流水线：

```text
标题切块 → 超大块二次切割 → 碎片块合并
```

`markdown_split_done` 标志位彻底消除重复切块，双阶段合并消除孤立标题行。

### 4. 切块可视化与统计面板

知识库详情页新增 Chunks 标签页：

- Token / 字符双维度分布直方图
- 总块数、平均 Token 数、平均字符数
- 逐块明细：内容预览、来源文件、Token/字符计数

### 5. 会话级 Token 监测

实时显示对话上下文 Token、RAG 附加 Token、总发送 Token，帮助研究者感知上下文窗口使用率。

### 6. 多模型 Manifold Pipe

附带三个即插即用的 Manifold Pipe，支持自定义中转地址、模型列表、API 密钥：

| Pipe | 特性 |
|------|------|
| [Anthropic Pipe](./anthropic_manifold_pipe.py) | Claude 4.6 adaptive thinking + 4.5 extended thinking，`-thinking` 后缀触发 |
| [Gemini Pipe](./google_gemini_pipe.py) | Gemini 3 thinkingLevel + 2.5 thinkingBudget，`-high`/`-thinking` 后缀触发 |
| [OpenAI Pipe](./openai_manifold_pipe.py) | 标准 OpenAI chat completions 格式 |

三个 Pipe 均支持 `chat:completion` usage 元数据上报。

---

## 技术架构

```
┌─────────────────────────────────────────────────┐
│  經緯·Contexture（材料层）                        │
│  PDF/图像 → 带页码锚点的结构化 Markdown            │
├─────────────────────────────────────────────────┤
│  Open WebUI AIH-Infra（检索层）← 本项目           │
│  Markdown 切块 → 向量化 → 混合检索 → LLM 生成     │
│  页码锚点贯穿全链路，输出自动附带学术引用           │
├─────────────────────────────────────────────────┤
│  Graph RAG / Agent RAG（理解层）→ 规划中           │
└─────────────────────────────────────────────────┘
```

---

## 快速开始

### Docker 部署

```bash
docker build -t open-webui-aih-infra .
docker run -d -p 3000:8080 \
  -v open-webui:/app/backend/data \
  --name open-webui-aih-infra \
  open-webui-aih-infra
```

### 安装 Manifold Pipe

1. 进入 Open WebUI → 管理 → Functions
2. 导入 `anthropic_manifold_pipe.py` / `google_gemini_pipe.py` / `openai_manifold_pipe.py`
3. 在 Valves 中配置 API 密钥和中转地址

---

## 改动文件清单

**后端**（9 文件修改 + 1 新增）

| 文件 | 改动 |
|------|------|
| `models/knowledge.py` | Knowledge 表新增 chunk_size/chunk_overlap/text_splitter 列 |
| `routers/retrieval.py` | 切块流水线重构（最大改动）|
| `routers/knowledge.py` | 知识库路由 + chunks API |
| `utils/middleware.py` | RAG 参数注入 + Token 计数 |
| `main.py` | 会话级 RAG 参数提取 |
| `routers/files.py` | 文件上传传递切块参数 |
| `retrieval/utils.py` | global_top_k 检索逻辑 |
| `tools/builtin.py` | 内置工具函数增强 |
| `utils/tools.py` | 工具元数据传递 |
| `migrations/versions/add_knowledge_rag_params.py` | **新增** DB 迁移 |

**前端**（8 文件修改 + 3 新增）

| 文件 | 改动 |
|------|------|
| `RAGParams.svelte` | **新增** 会话级 RAG 参数组件 |
| `Chunks.svelte` | **新增** 切块可视化组件 |
| `tokenCounter.ts` | **新增** Token 估算工具 |
| `Chat.svelte` | Token 监测 UI |
| `Controls.svelte` | RAG 参数面板入口 |
| `KnowledgeBase.svelte` | Chunks 标签页 |
| `CreateKnowledgeBase.svelte` | 创建时设置切块参数 |
| 其他 4 文件 | API 扩展、版本标识、列表显示 |

详见 [AIH-Infra 技术改造手册](./AIH-Infra_技术改造手册.md)。

---

## 与上游的关系

本项目是 Open WebUI 的 fork 分支，不是独立项目。改动遵循以下原则：

- 所有新增字段 nullable，不破坏原有数据
- 核心逻辑使用守卫模式（`markdown_split_done`、`if param is not None`），与原版代码并行而非替换
- 有 Alembic 迁移脚本，DB 变更可追踪、可回滚

升级策略：`git fetch upstream` → `git merge` → 解决冲突（集中在少数文件）→ 测试 → 发布。

---

## 项目生态

| 项目 | 定位 |
|------|------|
| **經緯·Contexture** | 材料层 — PDF/图像 → 带页码锚点的结构化 Markdown |
| **Open WebUI AIH-Infra** | 检索层 — 可追溯的朴素 RAG（本项目）|
| Graph RAG 集成 | 概念层 — 规划中 |
| Agent RAG 原型 | 研究层 — 规划中 |

---

## 致谢

- [Open WebUI](https://github.com/open-webui/open-webui) — Timothy J. Baek 及社区
- AIH-Infra 由 Güriedrich & Baireinhold 发起

---

> *经纬所织，是文献与技术的交汇；所守，是真实与可追溯的底线。*
