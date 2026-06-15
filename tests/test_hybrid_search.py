"""
混合检索模块测试
"""

from app.core.hybrid_searcher import BM25Searcher, HybridSearcher, SearchCandidate


def test_bm25_basic():
    """测试 BM25 关键词检索"""
    documents = [
        SearchCandidate(text="智能客服系统", source="doc1", doc_type="document", chunk_index=0),
        SearchCandidate(text="成本核算功能介绍", source="doc2", doc_type="document", chunk_index=1),
        SearchCandidate(text="AI 客服问答", source="doc3", doc_type="document", chunk_index=2),
    ]

    bm25 = BM25Searcher()
    bm25.fit(documents)

    results = bm25.search("智能客服", top_k=3)
    assert len(results) > 0
    # "智能客服系统" 应该最相关
    assert results[0][0].text == "智能客服系统"


def test_hybrid_search_fusion():
    """测试 RRF 融合检索"""
    vector_results = [
        {
            "text": "AI 大模型客服系统",
            "source": "doc1",
            "doc_type": "document",
            "chunk_index": 0,
            "similarity": 0.90,
        },
        {
            "text": "成本核算功能",
            "source": "doc2",
            "doc_type": "document",
            "chunk_index": 1,
            "similarity": 0.80,
        },
    ]

    documents = [
        SearchCandidate(
            text="AI 大模型客服系统", source="doc1", doc_type="document", chunk_index=0
        ),
        SearchCandidate(text="成本核算功能", source="doc2", doc_type="document", chunk_index=1),
        SearchCandidate(text="智能客服成本核算", source="doc3", doc_type="document", chunk_index=2),
    ]

    searcher = HybridSearcher()
    results = searcher.search(
        query="智能客服成本核算",
        vector_results=vector_results,
        documents=documents,
        vector_top_k=2,
        keyword_top_k=3,
        final_top_k=3,
    )

    assert len(results) == 3
    # doc3 在向量检索中没有，但关键词完全匹配，应该被召回
    sources = [r["source"] for r in results]
    assert "doc3" in sources


def test_hybrid_search_empty_documents():
    """测试无文档时回退到向量结果"""
    vector_results = [
        {
            "text": "AI 客服",
            "source": "doc1",
            "doc_type": "document",
            "chunk_index": 0,
            "similarity": 0.90,
        }
    ]

    searcher = HybridSearcher()
    results = searcher.search(
        query="AI 客服",
        vector_results=vector_results,
        documents=[],
        final_top_k=1,
    )

    assert len(results) == 1
    assert results[0]["source"] == "doc1"


def test_vector_store_hybrid_search():
    """测试 VectorStore 的 hybrid 参数"""
    from app.db.vector_store import LocalVectorStore

    store = LocalVectorStore()
    store.add_faqs(
        [
            {"question": "如何联系客服", "answer": "拨打 400 电话"},
        ]
    )
    store.add_chunks(
        [
            type(
                "C",
                (),
                {
                    "text": "智能客服系统支持成本核算",
                    "source": "doc1",
                    "doc_type": "document",
                    "chunk_index": 0,
                    "metadata": {},
                },
            )()
        ]
    )

    # 普通检索
    normal = store.search("客服", top_k=2, hybrid=False)
    assert len(normal["metadatas"][0]) > 0

    # 混合检索
    hybrid = store.search("智能客服成本核算", top_k=2, hybrid=True)
    assert len(hybrid["metadatas"][0]) > 0
