# 应有成本估算 AI 助手

基于 **RAG（检索增强生成）** 架构的企业级 AI 客服服务，支持语义理解 + 三级响应策略，确保回答准确、可控、低成本。

[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.109+-green.svg)](https://fastapi.tiangolo.com)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

## ✨ 特性

- 🧠 **语义理解**：基于 BGE Embedding，换种说法也能匹配到正确答案
- 🛡️ **防幻觉设计**：三级兜底策略（直接命中 / LLM 生成 / 拒绝回答）
- 💰 **成本极低**：80% 问题直接命中 FAQ，零 LLM 调用成本
- 📦 **开箱即用**：300 行代码，JSON 维护知识库，无需数据库
- 🔌 **多模型支持**：DeepSeek + SiliconFlow / OpenAI / Azure OpenAI 兼容接口

## 🚀 快速开始

### 方式一：本地运行（推荐开发）

```bash
# 1. 克隆项目
git clone https://github.com/your-org/ai-service.git
cd ai-service

# 2. 安装依赖
pip install -r requirements.txt

# 3. 配置环境变量
cp .env.example .env
# 编辑 .env，填入你的 API Key

# 4. 启动服务
python -m uvicorn app.main:app --host 0.0.0.0 --port 8082 --reload

# 5. 导入 FAQ 数据
python init_faq.py

# 6. 测试
# 访问 http://localhost:8082/docs 查看 API 文档
curl -X POST http://localhost:8082/chat/ask \
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
docker exec -it ai-service python init_faq.py

# 4. 验证
curl http://localhost:8082/chat/health
```

## 📁 项目结构

```
ai-service/
├── app/
│   ├── main.py              # FastAPI 入口
│   ├── config.py            # 环境变量配置（区分 local / api 模式）
│   ├── core/
│   │   ├── vector_store.py  # 向量存储（Local / API 两种后端）
│   │   └── faq_engine.py    # 问答引擎（三级兜底策略）
│   └── api/
│       ├── chat.py          # 对话接口
│       └── faq.py           # FAQ 管理接口
├── data/
│   └── faq.json             # FAQ 知识库（人工维护）
├── .env.example             # 环境变量模板（复制为 .env 后使用）
├── .gitignore               # Git 忽略规则（确保 .env 不被提交）
├── Dockerfile               # Docker 镜像构建
├── docker-compose.yml       # 一键 Docker 部署
├── init_faq.py              # FAQ 导入脚本
├── requirements.txt         # Python 依赖
└── README.md                # 本文档
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

### ⚠️ 重要安全提示

`.env` 文件包含你的真实 API Key，**绝不能提交到 Git**。项目已配置 `.gitignore`，确保 `.env` 被忽略。

## 🧠 核心机制

### 三级响应策略

```
用户提问
    ↓
① Embedding → 语义检索 Top-3 FAQ
    ↓
② 判断相似度：
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
| `POST /chat/ask` | 提问 | 核心接口，传入问题返回答案 |
| `GET /chat/health` | 健康检查 | 检查服务状态 |
| `POST /faq/seed` | 批量导入 | 清空并重新导入 FAQ（初始化用） |
| `POST /faq/add` | 单条添加 | 热更新，不重启服务 |
| `GET /faq/count` | 数量查询 | 查看当前 FAQ 总数 |
| `POST /faq/clear` | 清空 | 清空向量库 |

### 响应示例

```json
{
  "answer": "应有成本（Should Be Cost）是指...",
  "source": "faq",
  "confidence": 0.9507,
  "matched_question": "什么是应有成本？",
  "references": []
}
```

`source` 字段说明：
- `faq`：直接命中预设答案，零 LLM 成本
- `llm`：DeepSeek 基于上下文生成
- `reject`：相似度太低，拒绝回答

## 📝 FAQ 维护

### 数据结构

```json
[
  {
    "question": "什么是应有成本？",
    "answer": "应有成本是指..."
  }
]
```

### 维护方式

**批量导入（推荐初始化）**：

```bash
# 编辑 data/faq.json 后执行
python init_faq.py
```

**单条热更新（不重启服务）**：

```bash
curl -X POST http://localhost:8082/faq/add \
  -H "Content-Type: application/json" \
  -d '{"question":"新问题","answer":"新答案"}'
```

## 🛣️ 升级路线

- [ ] 流式输出（SSE 打字机效果）
- [ ] 多轮对话上下文
- [ ] 用户反馈收集（👍/👎）
- [ ] 文档知识库（PDF/Word 自动解析）
- [ ] 对话历史记录与分析看板

## 📄 License

[MIT](LICENSE) © pengyongjia
