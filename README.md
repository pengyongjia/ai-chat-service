# AI Chat Service

基于 **RAG（检索增强生成）** 架构的企业级 AI 客服服务，支持语义理解 + 三级响应策略，确保回答准确、可控、低成本。

[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.109+-green.svg)](https://fastapi.tiangolo.com)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

## ✨ 特性

- 🧠 **语义理解**：基于 BGE Embedding，换种说法也能匹配到正确答案
- 🛡️ **防幻觉设计**：三级兜底策略（直接命中 / LLM 生成 / 拒绝回答）
- 📄 **文档 RAG**：支持 PDF / Word / Excel / Markdown / TXT 自动解析入库
- 🔍 **检索优化**：混合检索（向量 + BM25）+ 重排序 + 查询重写 + 上下文压缩
- 💰 **成本极低**：80% 问题直接命中 FAQ，零 LLM 调用成本
- 📦 **开箱即用**：300 行代码，JSON 维护知识库，无需数据库
- 🔌 **多模型支持**：DeepSeek + SiliconFlow / OpenAI / Azure OpenAI 兼容接口
- ✅ **企业级工程化**：统一响应、异常处理、结构化日志、单元测试、Docker 部署

## 🚀 快速开始

### 方式一：本地运行（推荐开发）

```bash
# 1. 克隆项目
git clone https://github.com/pengyongjia/ai-chat-service.git
cd ai-chat-service

# 2. 安装依赖
pip install -r requirements.txt

# 3. 配置环境变量
cp .env.example .env
# 编辑 .env，填入你的 API Key

# 4. 启动服务
python -m uvicorn app.main:app --host 0.0.0.0 --port 8082 --reload

# 5. 导入 FAQ 数据
python scripts/init_knowledge.py

# 6. 测试
# 访问 http://localhost:8082/docs 查看 API 文档
curl -X POST http://localhost:8082/v1/chat/ask \
  -H "Content-Type: application/json" \
  -d '{"question":"什么是应有成本"}'
```

### 方式二：Docker 部署（推荐生产）

```bash
# 1. 配置环境变量
cp .env.example .env
# 编辑 .env，填入你的 API Key

# 2. 一键启动
docker-compose up -d

# 3. 导入 FAQ 数据
docker exec -it ai-service python scripts/init_knowledge.py

# 4. 验证
curl http://localhost:8082/health
```

## 📁 项目结构

```
ai-chat-service/
├── app/
│   ├── main.py                  # FastAPI 入口 + 全局异常处理
│   ├── config.py                # 配置管理 + 启动校验
│   ├── api/
│   │   ├── health.py            # 健康检查接口
│   │   └── v1/
│   │       ├── chat.py          # 对话接口
│   │       ├── faq.py           # FAQ 管理接口
│   │       └── knowledge.py     # 知识库管理接口
│   ├── core/
│   │   ├── context_compressor.py # 上下文压缩
│   │   ├── document_loader.py   # 多格式文档加载
│   │   ├── exceptions.py        # 自定义异常
│   │   ├── hybrid_searcher.py   # 混合检索（向量 + BM25）
│   │   ├── logging.py           # 结构化日志
│   │   ├── query_rewriter.py    # 查询重写
│   │   ├── reranker.py          # 检索结果重排序
│   │   ├── responses.py         # 统一响应格式
│   │   └── text_splitter.py     # 文本切分
│   ├── models/
│   │   ├── chat.py              # 聊天请求/响应模型
│   │   ├── common.py            # 通用模型
│   │   ├── faq.py               # FAQ 模型
│   │   └── knowledge.py         # 知识库模型
│   ├── services/
│   │   ├── chat_service.py      # 聊天业务逻辑
│   │   ├── faq_service.py       # FAQ 业务逻辑
│   │   ├── knowledge_service.py # 知识库业务逻辑
│   │   └── llm_client.py        # LLM 客户端封装
│   └── db/
│       └── vector_store.py      # 向量存储（Local / API 两种后端）
├── knowledge/
│   └── faq.json                 # FAQ 知识库（人工维护）
├── scripts/
│   └── init_knowledge.py        # FAQ 导入脚本
├── tests/                       # 单元测试
│   ├── conftest.py
│   ├── test_chat.py
│   ├── test_context_compressor.py
│   ├── test_faq.py
│   ├── test_hybrid_search.py
│   ├── test_knowledge.py
│   ├── test_query_rewriter.py
│   └── test_reranker.py
├── .env.example                 # 环境变量模板
├── .gitignore                   # Git 忽略规则
├── Dockerfile                   # Docker 镜像
├── docker-compose.yml           # Docker Compose 部署
├── pyproject.toml               # 项目配置 + 代码质量工具
├── requirements.txt             # Python 依赖
├── README.md                    # 本文档
└── DEPLOY.md                    # 部署文档
```

## 🔧 环境变量配置

复制 `.env.example` 为 `.env`，按需填写：

| 变量 | 必填 | 默认值 | 说明 |
|------|------|--------|------|
| `DEEPSEEK_API_KEY` | ✅ | — | DeepSeek API Key |
| `DEEPSEEK_BASE_URL` | — | `https://api.deepseek.com/v1` | DeepSeek API 地址 |
| `DEEPSEEK_MODEL` | — | `deepseek-chat` | 模型名称 |
| `EMBEDDING_MODE` | — | `api` | `local`=字符串匹配 / `api`=语义检索 |
| `EMBEDDING_API_KEY` | `api` 模式必填 | — | Embedding 服务 API Key |
| `EMBEDDING_API_URL` | — | `https://api.siliconflow.cn/v1` | 支持 SiliconFlow / OpenAI / Azure |
| `EMBEDDING_API_MODEL` | — | `BAAI/bge-large-zh-v1.5` | Embedding 模型 |
| `CHROMA_PERSIST_DIR` | — | `./chroma_db` | 向量数据库本地路径 |
| `FAQ_THRESHOLD_HIGH` | — | `0.75` | 高置信阈值（≥此值直接返回答案） |
| `FAQ_THRESHOLD_LOW` | — | `0.40` | 低置信阈值（<此值直接拒绝） |
| `FAQ_TOP_K` | — | `3` | 检索时返回的最相似 FAQ 数量 |
| `ENABLE_RERANK` | — | `true` | 是否启用重排序 |
| `ENABLE_HYBRID_SEARCH` | — | `true` | 是否启用混合检索（向量 + BM25） |
| `ENABLE_QUERY_REWRITE` | — | `false` | 是否启用查询重写（会调用 LLM） |
| `ENABLE_LLM_CONTEXT_COMPRESS` | — | `false` | 是否启用 LLM 上下文压缩（会调用 LLM） |
| `RERANK_VECTOR_WEIGHT` | — | `0.6` | 重排序向量相似度权重 |
| `RERANK_KEYWORD_WEIGHT` | — | `0.3` | 重排序关键词权重 |
| `RERANK_LENGTH_WEIGHT` | — | `0.1` | 重排序长度权重（三项和为 1.0） |
| `CONTEXT_SIMILARITY_THRESHOLD` | — | `0.35` | 上下文压缩相似度阈值 |
| `CONTEXT_MAX_CHUNK_LENGTH` | — | `600` | 单 chunk 最大长度 |
| `LOG_LEVEL` | — | `INFO` | 日志级别：DEBUG/INFO/WARNING/ERROR |

### ⚠️ 重要安全提示

`.env` 文件包含你的真实 API Key，**绝不能提交到 Git**。项目已配置 `.gitignore`，确保 `.env` 被忽略。

## 🧠 核心机制

### 三级响应策略

```
用户提问
    ↓
① 查询重写（可选）→ 把口语化问题标准化
    ↓
② 混合检索 → 向量语义检索 + BM25 关键词检索，RRF 融合
    ↓
③ 重排序 → 综合向量相似度、关键词匹配、FAQ 权重再精排
    ↓
④ 上下文压缩 → 过滤低相关 chunk，控制 LLM 上下文长度
    ↓
⑤ 判断相似度：
    ├─ ≥ 0.75 → 直接返回答案 (source: faq)          💰 成本：0
    ├─ 0.40~0.75 → DeepSeek 基于上下文生成 (source: llm)  💰 成本：~0.01元
    └─ < 0.40 → 拒绝回答，引导人工 (source: reject)   💰 成本：0
```

### 为什么用 RAG？

| 对比项 | 直接调 LLM | RAG + 三级兜底 |
|--------|-----------|---------------|
| 幻觉风险 | ⚠️ 高 | ✅ 极低 |
| 回答可控性 | ❌ 不可控 | ✅ 100% 可审计 |
| 月均成本 | ~300-500元 | ~5元 |
| 专业准确性 | 依赖训练数据 | 人工维护，精准可控 |

## 📚 API 接口

| 接口 | 方法 | 说明 |
|------|------|------|
| `POST /v1/chat/ask` | 提问 | 核心接口，传入问题返回答案 |
| `GET /health` | 健康检查 | 基础健康状态 |
| `GET /health/ready` | 就绪检查 | 包含依赖组件状态 |
| `POST /v1/faq/seed` | 批量导入 | 清空并重新导入 FAQ（初始化用） |
| `POST /v1/faq/add` | 单条添加 | 热更新，不重启服务 |
| `GET /v1/faq/count` | 数量查询 | 查看当前 FAQ 总数 |
| `POST /v1/faq/clear` | 清空 | 清空向量库 |
| `POST /v1/knowledge/upload` | 上传文档 | 上传 PDF/Word/Excel/MD/TXT 到知识库 |
| `GET /v1/knowledge/list` | 文档列表 | 列出已上传文档 |
| `GET /v1/knowledge/stats` | 知识库统计 | 查看 FAQ/文档数量 |
| `POST /v1/knowledge/delete` | 删除文档 | 删除指定文档 |
| `POST /v1/knowledge/clear-documents` | 清空文档 | 清空所有文档，保留 FAQ |

### 响应格式

所有接口统一返回：

```json
{
  "code": 0,
  "message": "success",
  "data": { ... }
}
```

### 聊天响应示例

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "answer": "应有成本（Should Be Cost）是指...",
    "source": "faq",
    "confidence": 0.9507,
    "matched_question": "什么是应有成本？",
    "references": []
  }
}
```

`source` 字段说明：
- `faq`：直接命中预设答案，零 LLM 成本
- `llm`：DeepSeek 基于上下文生成
- `reject`：相似度太低，拒绝回答

## 🧪 测试

```bash
# 运行单元测试
pytest

# 代码格式化
black app tests scripts
isort app tests scripts

# 代码检查
flake8 app tests scripts
```

## 📝 知识库维护

### FAQ 维护

**批量导入（推荐初始化）**：

```bash
# 编辑 knowledge/faq.json 后执行
python scripts/init_knowledge.py
```

**单条热更新（不重启服务）**：

```bash
curl -X POST http://localhost:8082/v1/faq/add \
  -H "Content-Type: application/json" \
  -d '{"question":"新问题","answer":"新答案"}'
```

### 文档知识库

支持上传以下格式文档：
- PDF（推荐安装 PyMuPDF，否则使用 pypdf）
- Word（.docx / .doc）
- Excel（.xlsx / .xls）
- CSV
- Markdown（.md）
- TXT

**上传文档**：

```bash
curl -X POST http://localhost:8082/v1/knowledge/upload \
  -F "file=@产品手册.pdf"
```

**查看知识库统计**：

```bash
curl http://localhost:8082/v1/knowledge/stats
```

**删除文档**：

```bash
curl -X POST http://localhost:8082/v1/knowledge/delete \
  -H "Content-Type: application/json" \
  -d '{"filename":"产品手册.pdf"}'
```

### 文档处理流程

```
上传文件
    ↓
DocumentLoader 解析文本
    ↓
TextSplitter 切分为 chunks（500 字/段，保留语义）
    ↓
Embedding API 生成向量
    ↓
ChromaDB 存储
    ↓
用户提问 → 查询重写 → 混合检索 → 重排序 → 上下文压缩
    ↓
LLM 基于上下文生成回答
```

### 检索优化说明

| 优化模块 | 作用 | 默认状态 | 成本影响 |
|----------|------|----------|----------|
| **混合检索** | 向量检索 + BM25 关键词检索互补，提升专业术语召回 | 开启 | 无额外成本 |
| **重排序** | 综合语义、关键词、长度、FAQ 权重精排 Top-K | 开启 | 无额外成本 |
| **查询重写** | 把口语化问题改写为标准查询，提高检索准确率 | 关闭 | 每次查询多调 1 次 LLM |
| **上下文压缩** | 过滤/摘要低相关 chunks，提升 LLM 生成质量 | 关闭 | 仅对长 chunk 调 LLM |

**本地效果测试**：

```bash
# 配置真实 API Key 后运行
python scripts/test_phase3.py
```

## 🛣️ 升级路线

- [x] 文档知识库（PDF/Word 自动解析）
- [x] 重排序 + 混合检索
- [ ] 流式输出（SSE 打字机效果）
- [ ] 多轮对话上下文
- [ ] 用户反馈收集（👍/👎）
- [ ] 对话历史记录与分析看板

## 📄 License

[MIT](LICENSE) © pengyongjia
