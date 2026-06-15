"""
重排序模块测试
"""

import pytest

from app.core.reranker import Reranker


def test_reranker_basic():
    """测试基础重排序功能"""
    reranker = Reranker(vector_weight=0.6, keyword_weight=0.3, length_weight=0.1)

    candidates = [
        {
            "text": "产品 A 支持自动成本核算功能",
            "source": "doc1",
            "doc_type": "document",
            "chunk_index": 0,
            "similarity": 0.60,
        },
        {
            "text": "什么是成本核算？",
            "source": "faq",
            "doc_type": "faq",
            "chunk_index": 0,
            "similarity": 0.70,
            "answer": "成本核算是计算产品成本的过程。",
        },
        {
            "text": "成本核算",
            "source": "doc2",
            "doc_type": "document",
            "chunk_index": 0,
            "similarity": 0.80,
        },
    ]

    results = reranker.rerank("成本核算怎么做", candidates, top_k=3)

    assert len(results) == 3
    # 高相似度 + 完整关键词匹配应该排第一
    assert results[0].text == "成本核算"


def test_reranker_keyword_bonus():
    """测试关键词匹配奖励"""
    reranker = Reranker(vector_weight=0.5, keyword_weight=0.4, length_weight=0.1)

    candidates = [
        {
            "text": "这是一段完全不相关的内容",
            "source": "doc1",
            "doc_type": "document",
            "chunk_index": 0,
            "similarity": 0.90,
        },
        {
            "text": "智能客服系统支持成本核算功能",
            "source": "doc2",
            "doc_type": "document",
            "chunk_index": 0,
            "similarity": 0.50,
        },
    ]

    results = reranker.rerank("智能客服成本核算", candidates, top_k=2)

    # 虽然向量相似度低，但关键词全部命中，应该排到第一
    assert results[0].text == "智能客服系统支持成本核算功能"


def test_reranker_faq_bonus():
    """测试 FAQ 类型加权"""
    reranker = Reranker(vector_weight=0.6, keyword_weight=0.3, length_weight=0.1)

    candidates = [
        {
            "text": "如何联系客服？",
            "source": "faq",
            "doc_type": "faq",
            "chunk_index": 0,
            "similarity": 0.70,
            "answer": "拨打 400 电话。",
        },
        {
            "text": "如何联系客服部门并获得技术支持",
            "source": "doc1",
            "doc_type": "document",
            "chunk_index": 0,
            "similarity": 0.72,
        },
    ]

    results = reranker.rerank("怎么联系客服", candidates, top_k=2)

    # FAQ 应该获得额外加分后排第一
    assert results[0].doc_type == "faq"


def test_reranker_empty_candidates():
    """测试空候选列表"""
    reranker = Reranker()
    results = reranker.rerank("测试", [])
    assert results == []


def test_reranker_weight_validation():
    """测试权重校验"""
    with pytest.raises(ValueError):
        Reranker(vector_weight=0.5, keyword_weight=0.3, length_weight=0.1)
