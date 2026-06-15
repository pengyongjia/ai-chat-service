"""
第三阶段检索优化效果测试脚本

用法：
1. 复制 .env.example 为 .env，填入真实 API Key
2. 运行：python scripts/test_phase3.py

本脚本仅用于本地效果验证，不会提交任何数据。
"""

import sys
from pathlib import Path

from dotenv import load_dotenv

# 加载 .env 并添加项目根目录到路径
load_dotenv(Path(__file__).parent.parent / ".env")
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.config import config
from app.core.reranker import reranker
from app.db.vector_store import APIEmbeddingStore, Chunk

SAMPLE_FAQS = [
    {"question": "如何注册账号", "answer": "访问官网点击注册，填写手机号和验证码即可。"},
    {"question": "支持哪些文件格式", "answer": "支持 PDF、Word、Excel、CSV、Markdown、TXT。"},
    {"question": "如何联系客服", "answer": "拨打 400-xxx-xxxx 或发送邮件至 support@example.com。"},
]

SAMPLE_DOCUMENT = """
应有成本估算平台是一款面向制造业的 SaaS 产品。
核心功能包括：BOM 成本拆解、工艺路线估算、供应商报价管理、模具费用分摊等。
用户可以通过上传 Excel 报价单，系统自动识别材料、工序、工时，并生成成本分析报告。
系统支持多租户模式，不同企业之间的数据完全隔离。
AI 客服模块可以基于企业上传的产品手册和 FAQ 回答客户咨询。
"""


def build_vector_store():
    """构建测试向量库"""
    print("正在构建测试向量库...")
    store = APIEmbeddingStore()
    store.clear()

    # 导入 FAQ
    store.add_faqs(SAMPLE_FAQS)

    # 导入文档 chunks
    chunks = []
    for i, para in enumerate(SAMPLE_DOCUMENT.strip().split("\n")):
        para = para.strip()
        if para:
            chunks.append(
                Chunk(
                    text=para,
                    source="产品手册.txt",
                    doc_type="document",
                    chunk_index=i,
                )
            )
    store.add_chunks(chunks)
    print(f"已导入 {len(SAMPLE_FAQS)} 条 FAQ，{len(chunks)} 个文档 chunks\n")
    return store


def test_normal_search(store, query: str):
    """测试普通向量检索"""
    print(f"[普通向量检索] 查询: {query}")
    results = store.search(query, top_k=3, doc_types=["faq", "document"], hybrid=False)
    for i, meta in enumerate(results["metadatas"][0], 1):
        sim = 1 - results["distances"][0][i - 1]
        print(f"  {i}. [{meta.get('doc_type')}] {meta.get('text')[:60]}... (相似度: {sim:.3f})")
    print()


def test_hybrid_and_rerank(store, query: str):
    """测试混合检索 + 重排序"""
    print(f"[混合检索 + 重排序] 查询: {query}")

    # 混合检索
    results = store.search(query, top_k=5, doc_types=["faq", "document"], hybrid=True)
    candidates = []
    for i, meta in enumerate(results["metadatas"][0]):
        sim = 1 - results["distances"][0][i]
        candidates.append(
            {
                "text": meta.get("text", ""),
                "answer": meta.get("answer", ""),
                "source": meta.get("source", ""),
                "doc_type": meta.get("doc_type", "document"),
                "chunk_index": meta.get("chunk_index", 0),
                "similarity": sim,
                "metadata": meta,
            }
        )

    # 重排序
    ranked = reranker.rerank(query, candidates, top_k=3)
    for i, item in enumerate(ranked, 1):
        scores = f"综合: {item.final_score:.3f}, 向量: {item.vector_score:.3f}"
        keyword = f"关键词: {item.keyword_score:.3f}"
        print(f"  {i}. [{item.doc_type}] {item.text[:50]}... ({scores}, {keyword})")
    print()


def check_config():
    """检查配置"""
    if not config.DEEPSEEK_API_KEY or "your" in config.DEEPSEEK_API_KEY:
        print("错误：请先在 .env 中配置有效的 DEEPSEEK_API_KEY")
        return False
    if (
        config.EMBEDDING_MODE != "api"
        or not config.EMBEDDING_API_KEY
        or "your" in config.EMBEDDING_API_KEY
    ):
        print("错误：请先在 .env 中配置 EMBEDDING_MODE=api 和有效的 EMBEDDING_API_KEY")
        return False
    return True


def main():
    if not check_config():
        return

    store = build_vector_store()

    queries = [
        "怎么注册",
        "能传什么文件",
        "如何找客服",
        "成本分析怎么做的",
        "系统支持哪些功能",
    ]

    for query in queries:
        test_normal_search(store, query)
        test_hybrid_and_rerank(store, query)
        print("-" * 80)


if __name__ == "__main__":
    main()
