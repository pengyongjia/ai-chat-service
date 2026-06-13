# 应有成本估算 AI 助手 - 部署与使用文档

## 一、项目概述

独立部署的 AI 客服服务，基于 FastAPI + 轻量级文本匹配实现 FAQ 智能问答，与芋道后端完全解耦。

**核心流程**：
```
用户提问 → 文本相似度匹配 Top-3 FAQ → 相似度 ≥ 0.75 直接返回答案
                                    → 否则调用 DeepSeek 生成回答
```

**技术栈**：
- FastAPI（Web 框架）
- ChromaDB（向量数据库，当前使用轻量字符串匹配替代 Embedding）
- DeepSeek API（兜底生成）
- difflib.SequenceMatcher（FAQ 匹配引擎）

---

## 二、目录结构

```
ai-service/
├── app/
│   ├── main.py              # FastAPI 入口
│   ├── config.py            # 配置读取
│   ├── core/
│   │   ├── vector_store.py  # FAQ 存储与检索（轻量版）
│   │   └── faq_engine.py    # 问答引擎（匹配 + DeepSeek）
│   └── api/
│       ├── chat.py          # 对话接口 POST /chat/ask
│       └── faq.py           # FAQ 管理接口
├── data/
│   └── faq.json             # FAQ 数据源（人工维护）
├── init_faq.py              # 一键导入脚本
├── .env                     # 环境变量（API Key 等）
├── .env.example             # 环境变量模板
└── requirements.txt         # Python 依赖
```

---

## 三、环境配置

### 1. 安装依赖

```bash
cd ai-service
pip install fastapi uvicorn chromadb openai python-dotenv -i https://pypi.tuna.tsinghua.edu.cn/simple
```

### 2. 配置环境变量

复制模板并编辑：

```bash
cp .env.example .env
```

编辑 `.env`：

```env
# DeepSeek API 配置（必填）
DEEPSEEK_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxx
DEEPSEEK_BASE_URL=https://api.deepseek.com/v1
DEEPSEEK_MODEL=deepseek-chat

# 服务配置
CHROMA_PERSIST_DIR=./chroma_db
EMBEDDING_MODEL=BAAI/bge-small-zh-v1.5
FAQ_THRESHOLD=0.75
FAQ_TOP_K=3
```

> **获取 DeepSeek API Key**：访问 https://platform.deepseek.com 注册并创建 API Key

---

## 四、启动服务

### 方式一：直接启动（推荐开发环境）

```bash
cd ai-service
python -m uvicorn app.main:app --host 0.0.0.0 --port 8082 --reload
```

### 方式二：后台启动（生产环境）

```bash
nohup python -m uvicorn app.main:app --host 0.0.0.0 --port 8082 > ai-service.log 2>&1 &
```

### 验证服务

```bash
curl http://localhost:8082/
# 预期返回：{"service": "应有成本估算 AI 助手", "version": "0.1.0", "docs": "/docs"}
```

---

## 五、导入 FAQ 数据

### 首次启动必做

```bash
cd ai-service
python init_faq.py
```

预期输出：`成功导入 12 条 FAQ`

### 查看 FAQ 数量

```bash
curl http://localhost:8082/faq/count
```

---

## 六、API 接口说明

### 1. 用户提问（核心接口）

```http
POST /chat/ask
Content-Type: application/json

{
  "question": "如何申请试用"
}
```

**返回示例**：

```json
{
  "answer": "您可以点击页面上的【立即体验】按钮...",
  "source": "faq",
  "confidence": 0.9231,
  "matched_question": "如何申请试用？",
  "references": []
}
```

| 字段 | 说明 |
|------|------|
| `source` | `faq` = 命中预设答案，`llm` = DeepSeek 生成，`error` = 异常 |
| `confidence` | 匹配相似度（0-1），越高越准确 |
| `matched_question` | 匹配到的原始问题 |

### 2. 单条添加 FAQ

```http
POST /faq/add
Content-Type: application/json

{
  "question": "新问题",
  "answer": "新答案"
}
```

### 3. 批量覆盖导入（清空旧数据）

```http
POST /faq/seed
Content-Type: application/json

{
  "faqs": [
    {"question": "问题1", "answer": "答案1"},
    {"question": "问题2", "answer": "答案2"}
  ]
}
```

### 4. 清空 FAQ

```http
POST /faq/clear
```

### 5. FAQ 数量查询

```http
GET /faq/count
```

---

## 七、FAQ 数据源管理

### 当前内置 FAQ（12 条）

| # | 问题 | 适用场景 |
|---|------|---------|
| 1 | 什么是应有成本估算？ | 产品概念解释 |
| 2 | 你们系统适合什么类型的企业？ | 行业定位 |
| 3 | 零基估算和对标估算有什么区别？ | 功能差异 |
| 4 | 如何申请试用？ | 试用流程 |
| 5 | 系统支持私有化部署吗？ | 部署方式 |
| 6 | 上线周期大概多久？ | 实施周期 |
| 7 | 你们的成本数据从哪来？ | 数据来源 |
| 8 | 系统能对接我们的 ERP 吗？ | 系统集成 |
| 9 | 报价单可以直接导入系统分析吗？ | 功能使用 |
| 10 | 降本空间是怎么算出来的？ | 核心指标 |
| 11 | 你们的收费模式是什么？ | 定价策略 |
| 12 | 估算结果可靠吗？ | 准确性说明 |

### 扩展 FAQ 的方法

**方法 A：直接编辑 JSON（推荐）**

1. 打开 `data/faq.json`
2. 按格式添加新问题：

```json
{
  "question": "新问题文本",
  "answer": "对应的回答文本"
}
```

3. 保存后执行 `python init_faq.py` 重新导入

**方法 B：调 API（热更新，不重启服务）**

```bash
# 单条添加
curl -X POST http://localhost:8082/faq/add \
  -H "Content-Type: application/json" \
  -d '{"question":"支持哪些浏览器？","answer":"支持 Chrome、Edge、Firefox 等现代浏览器，IE11 兼容模式也可使用。"}'
```

### 建议补充的 FAQ 方向

- 账号权限与人数限制
- 数据安全与备份策略
- 培训与实施方式
- 退款/续费政策
- 移动端访问支持
- 具体行业成功案例细节
- 系统性能与并发能力

---

## 八、门户网站对接

门户网站的 AI 悬浮助手已配置，API 地址：

```javascript
// portal/index.html
var AI_API_URL = 'http://localhost:8082/chat/ask';
```

如果 AI 服务部署到其他服务器，修改此地址即可。

---

## 九、常见问题排查

### Q1: 服务启动报错 `端口被占用`

```bash
# 查看占用端口的进程
netstat -ano | findstr :8082
# 杀掉进程
taskkill //F //PID <PID>
```

### Q2: FAQ 导入超时

首次导入时如果网络较慢，增加超时时间：

```python
# init_faq.py 中修改
resp = requests.post(API_URL, json={"faqs": faqs}, timeout=300)
```

### Q3: DeepSeek API 调用失败

检查 `.env` 中的 `DEEPSEEK_API_KEY` 是否正确，以及余额是否充足。

### Q4: 回答匹配不准确

- 检查 `FAQ_THRESHOLD`（默认 0.75），适当降低可提高召回率
- 优化 FAQ 问题的表述，使其更接近用户实际提问方式
- 补充更多相似问法到 FAQ 中

---

## 十、升级路线图

| 阶段 | 功能 | 优先级 |
|------|------|--------|
| 当前 | FAQ 文本匹配 + DeepSeek 兜底 | ✅ |
| 短期 | Embedding 语义检索（网络恢复后） | 中 |
| 中期 | 对话历史记录、上下文理解 | 低 |
| 长期 | 成本估算引导式对话 | 低 |
