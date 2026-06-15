"""
上下文压缩模块测试
"""

from app.core.context_compressor import ContextCompressor


def test_compress_filter_by_threshold():
    """测试按相似度阈值过滤"""
    compressor = ContextCompressor(similarity_threshold=0.5)

    candidates = [
        {"text": "相关内容 A", "similarity": 0.8},
        {"text": "相关内容 B", "similarity": 0.6},
        {"text": "不相关内容", "similarity": 0.2},
    ]

    results = compressor.compress("测试", candidates, max_total_length=1000)
    assert len(results) == 2
    assert all(r["similarity"] >= 0.5 for r in results)


def test_compress_keep_best_when_all_filtered():
    """测试全部过滤后保留最优一条"""
    compressor = ContextCompressor(similarity_threshold=0.9)

    candidates = [
        {"text": "内容 A", "similarity": 0.3},
        {"text": "内容 B", "similarity": 0.5},
    ]

    results = compressor.compress("测试", candidates, max_total_length=1000)
    assert len(results) == 1
    assert results[0]["text"] == "内容 B"


def test_compress_truncate_long_text():
    """测试长文本截断"""
    compressor = ContextCompressor(similarity_threshold=0.0, max_chunk_length=10)

    candidates = [
        {"text": "这是一段非常长的文本内容需要被截断", "similarity": 0.9},
    ]

    results = compressor.compress("测试", candidates, max_total_length=1000)
    assert len(results[0]["text"]) <= 14  # 10 字符 + "..."
    assert results[0]["text"].endswith("...")


def test_compress_total_length_limit():
    """测试总长度限制"""
    compressor = ContextCompressor(similarity_threshold=0.0, max_chunk_length=1000)

    candidates = [
        {"text": "A" * 300, "similarity": 0.9},
        {"text": "B" * 300, "similarity": 0.8},
        {"text": "C" * 300, "similarity": 0.7},
    ]

    results = compressor.compress("测试", candidates, max_total_length=500)
    total = sum(len(r["text"]) for r in results)
    assert total <= 500


def test_compress_empty_candidates():
    """测试空候选"""
    compressor = ContextCompressor()
    assert compressor.compress("测试", []) == []
