"""
混合检索模块
结合向量语义检索与 BM25 关键词检索，通过 RRF 融合提升召回率
"""

import math
import re
from dataclasses import dataclass

from app.core.logging import log


@dataclass
class SearchCandidate:
    """检索候选结果"""

    text: str
    source: str
    doc_type: str
    chunk_index: int
    answer: str = ""
    metadata: dict | None = None


class BM25Searcher:
    """
    简化版 BM25 关键词检索器

    不依赖外部库，适合中小规模知识库。
    后续可替换为 rank-bm25 等专业实现。
    """

    def __init__(self, k1: float = 1.5, b: float = 0.75):
        """
        Args:
            k1: 词频饱和度参数
            b: 文档长度归一化参数
        """
        self.k1 = k1
        self.b = b
        self.documents: list[SearchCandidate] = []
        self.tokenized_docs: list[list[str]] = []
        self.idf: dict[str, float] = {}
        self.avg_doc_len = 0.0

    def fit(self, documents: list[SearchCandidate]):
        """构建 BM25 索引"""
        self.documents = documents
        self.tokenized_docs = [self._tokenize(d.text) for d in documents]

        total_len = sum(len(tokens) for tokens in self.tokenized_docs)
        self.avg_doc_len = total_len / len(documents) if documents else 0.0

        # 计算 IDF
        df = {}
        for tokens in self.tokenized_docs:
            seen = set(tokens)
            for token in seen:
                df[token] = df.get(token, 0) + 1

        n = len(documents)
        self.idf = {token: math.log((n - f + 0.5) / (f + 0.5) + 1.0) for token, f in df.items()}

    def search(self, query: str, top_k: int = 20) -> list[tuple[SearchCandidate, float]]:
        """
        执行 BM25 检索

        Returns:
            按分数降序排列的 (candidate, score) 列表
        """
        if not self.documents or not self.idf:
            return []

        query_tokens = self._tokenize(query)
        if not query_tokens:
            return []

        scored = []
        for i, doc_tokens in enumerate(self.tokenized_docs):
            score = self._score(query_tokens, doc_tokens)
            if score > 0:
                scored.append((self.documents[i], score))

        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[:top_k]

    def _score(self, query_tokens: list[str], doc_tokens: list[str]) -> float:
        """计算单条文档的 BM25 分数"""
        doc_len = len(doc_tokens)
        token_freq = {}
        for token in doc_tokens:
            token_freq[token] = token_freq.get(token, 0) + 1

        score = 0.0
        for token in query_tokens:
            if token not in token_freq:
                continue
            idf = self.idf.get(token, 0.0)
            tf = token_freq[token]
            denom = tf + self.k1 * (1 - self.b + self.b * doc_len / self.avg_doc_len)
            score += idf * (tf * (self.k1 + 1)) / denom
        return score

    def _tokenize(self, text: str) -> list[str]:
        """轻量级中文分词（2-gram + 3-gram）"""
        if not text:
            return []

        text = text.lower()
        tokens = re.findall(r"[a-z0-9]+", text)

        for chars in re.findall(r"[一-龥]+", text):
            if len(chars) < 2:
                continue
            for i in range(len(chars) - 1):
                tokens.append(chars[i : i + 2])
            if len(chars) >= 3:
                for i in range(len(chars) - 2):
                    tokens.append(chars[i : i + 3])

        return tokens


class HybridSearcher:
    """
    混合检索器

    流程：
    1. 向量检索获取语义相关结果
    2. BM25 检索获取关键词相关结果
    3. 使用 RRF（Reciprocal Rank Fusion）融合两种排序
    """

    def __init__(self, rrk_k: float = 60.0):
        """
        Args:
            rrk_k: RRF 融合参数，通常取 60
        """
        self.rrk_k = rrk_k
        self.bm25 = BM25Searcher()

    def search(
        self,
        query: str,
        vector_results: list[dict],
        documents: list[SearchCandidate],
        vector_top_k: int = 10,
        keyword_top_k: int = 10,
        final_top_k: int = 5,
    ) -> list[dict]:
        """
        执行混合检索

        Args:
            query: 查询文本
            vector_results: 向量检索结果，每项包含 text/source/doc_type/similarity 等
            documents: 全部文档候选，用于 BM25 检索
            vector_top_k: 向量检索参与融合的数量
            keyword_top_k: 关键词检索参与融合的数量
            final_top_k: 最终结果数量

        Returns:
            融合排序后的结果列表
        """
        if not documents:
            return vector_results[:final_top_k]

        # 限制向量结果数量
        vector_results = vector_results[:vector_top_k]

        # 构建 BM25 索引并检索
        self.bm25.fit(documents)
        keyword_results = self.bm25.search(query, top_k=keyword_top_k)

        # RRF 融合
        fused = self._rrf_fuse(vector_results, keyword_results)

        log.info(
            f"混合检索完成: 向量 {len(vector_results)} 条, "
            f"关键词 {len(keyword_results)} 条, 融合后 {len(fused)} 条"
        )

        return fused[:final_top_k]

    def _rrf_fuse(
        self,
        vector_results: list[dict],
        keyword_results: list[tuple[SearchCandidate, float]],
    ) -> list[dict]:
        """
        RRF 融合两种排序

        score = Σ 1 / (k + rank)
        """
        scores: dict[str, float] = {}
        entries: dict[str, dict] = {}

        # 向量检索排名
        for rank, item in enumerate(vector_results):
            key = self._make_key(item)
            scores[key] = scores.get(key, 0.0) + 1.0 / (self.rrk_k + rank + 1)
            entries[key] = item

        # 关键词检索排名
        for rank, (candidate, _) in enumerate(keyword_results):
            key = self._make_key_from_candidate(candidate)
            # 合并时优先保留向量检索的结果（它包含 similarity）
            if key not in entries:
                entries[key] = {
                    "text": candidate.text,
                    "source": candidate.source,
                    "doc_type": candidate.doc_type,
                    "chunk_index": candidate.chunk_index,
                    "similarity": 0.0,  # BM25 没有语义相似度，设为 0
                    "answer": candidate.answer,
                    "metadata": candidate.metadata or {},
                }
            scores[key] = scores.get(key, 0.0) + 1.0 / (self.rrk_k + rank + 1)

        # 排序
        sorted_keys = sorted(scores.keys(), key=lambda k: scores[k], reverse=True)
        return [entries[k] for k in sorted_keys]

    def _make_key(self, item: dict) -> str:
        """为向量结果生成唯一键"""
        return f"{item.get('source', '')}#{item.get('chunk_index', 0)}#{item.get('text', '')[:50]}"

    def _make_key_from_candidate(self, candidate: SearchCandidate) -> str:
        """为 BM25 候选生成唯一键"""
        return f"{candidate.source}#{candidate.chunk_index}#{candidate.text[:50]}"


# 全局混合检索器实例
hybrid_searcher = HybridSearcher()
