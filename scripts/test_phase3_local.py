"""
第三阶段检索优化本地效果测试脚本（无需 API Key）

用法：
python scripts/test_phase3_local.py

本脚本使用 LocalVectorStore，仅验证混合检索和重排序效果。
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.reranker import reranker
from app.db.vector_store import LocalVectorStore


def build_store():
    """构建本地测试向量库"""
    print("正在构建本地测试向量库...")
    store = LocalVectorStore()

    # FAQ
    store.add_faqs(
        [
            {"question": "如何注册账号", "answer": "访问官网点击注册即可。"},
            {"question": "支持哪些文件格式", "answer": "支持 PDF、Word、Excel 等。"},
            {"question": "如何联系客服", "answer": "拨打 400 电话。"},
        ]
    )

    # 文档 chunks
    store.add_chunks(
        [
            type(
                "Chunk",
                (),
                {
                    "text": "应有成本估算平台是一款面向制造业的 SaaS 产品，支持 BOM 成本拆解。",
                    "source": "产品手册.txt",
                    "doc_type": "document",
                    "chunk_index": 0,
                    "metadata": {},
                },
            )(),
            type(
                "Chunk",
                (),
                {
                    "text": "系统支持多租户模式，不同企业之间的数据完全隔离。",
                    "source": "产品手册.txt",
                    "doc_type": "document",
                    "chunk_index": 1,
                    "metadata": {},
                },
            )(),
            type(
                "Chunk",
                (),
                {
                    "text": "AI 客服模块可以基于企业上传的产品手册和 FAQ 回答客户咨询。",
                    "source": "产品手册.txt",
                    "doc_type": "document",
                    "chunk_index": 2,
                    "metadata": {},
                },
            )(),
        ]
    )
    print("向量库构建完成\n")
    return store


def test_search(store, query: str, hybrid: bool):
    """测试检索效果"""
    mode = "混合检索" if hybrid else "普通检索"
    print(f"[{mode}] 查询: {query}")

    results = store.search(query, top_k=3, doc_types=["faq", "document"], hybrid=hybrid)
    candidates = []
    for i, meta in enumerate(results["metadatas"][0], 1):
        sim = 1 - results["distances"][0][i - 1]
        candidates.append(
            {
                "text": meta.get("text", ""),
                "answer": meta.get("answer", ""),
                "source": meta.get("source", ""),
                "doc_type": meta.get("doc_type", "document"),
                "chunk_index": meta.get("chunk_index", 0),
                "similarity": sim,
            }
        )
        print(f"  {i}. [{meta.get('doc_type')}] {meta.get('text')[:50]}... (相似度: {sim:.3f})")

    # 重排序
    ranked = reranker.rerank(query, candidates, top_k=3)
    print("  重排序后:")
    for i, item in enumerate(ranked, 1):
        print(
            f"    {i}. [{item.doc_type}] {item.text[:50]}... "
            f"(综合: {item.final_score:.3f}, 向量: {item.vector_score:.3f}, "
            f"关键词: {item.keyword_score:.3f})"
        )
    print()


def main():
    store = build_store()

    queries = [
        "怎么注册",
        "能传什么文件",
        "如何找客服",
        "成本分析怎么做的",
        "系统支持哪些功能",
    ]

    for query in queries:
        test_search(store, query, hybrid=False)
        test_search(store, query, hybrid=True)
        print("-" * 80)


if __name__ == "__main__":
    main()
