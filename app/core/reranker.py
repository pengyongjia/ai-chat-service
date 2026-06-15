"""
重排序模块
对初步检索结果进行综合打分排序，提升最终进入 LLM 的上下文质量
"""

import re
from dataclasses import dataclass

from app.core.logging import log


@dataclass
class RankedCandidate:
    """重排序后的候选结果"""

    text: str
    source: str
    doc_type: str
    chunk_index: int
    vector_score: float
    keyword_score: float
    final_score: float
    answer: str = ""
    metadata: dict | None = None


class Reranker:
    """
    轻量级重排序器

    综合考虑：
    - 向量语义相似度
    - 关键词匹配度（TF-IDF 简化版）
    - 文档类型权重（FAQ 优先）
    - 位置/长度惩罚
    """

    # FAQ 在重排序时的额外权重
    FAQ_BONUS = 0.05
    # 关键词覆盖完整匹配的奖励
    KEYWORD_FULL_MATCH_BONUS = 0.10

    def __init__(
        self,
        vector_weight: float = 0.6,
        keyword_weight: float = 0.3,
        length_weight: float = 0.1,
    ):
        """
        Args:
            vector_weight: 向量相似度权重
            keyword_weight: 关键词匹配权重
            length_weight: 长度合理度权重
        """
        if abs(vector_weight + keyword_weight + length_weight - 1.0) > 1e-6:
            raise ValueError("三个权重之和必须等于 1.0")

        self.vector_weight = vector_weight
        self.keyword_weight = keyword_weight
        self.length_weight = length_weight

    def rerank(self, query: str, candidates: list[dict], top_k: int = 5) -> list[RankedCandidate]:
        """
        对候选结果重排序

        Args:
            query: 用户查询
            candidates: 初步检索结果列表，每项包含 text/source/doc_type/similarity 等
            top_k: 返回前 K 个

        Returns:
            重排序后的候选列表
        """
        if not candidates:
            return []

        query_tokens = self._tokenize(query)

        ranked = []
        for item in candidates:
            vector_score = item.get("similarity", 0.0)
            keyword_score = self._keyword_score(query_tokens, item.get("text", ""))
            length_score = self._length_score(item.get("text", ""))

            # FAQ 类型额外加分
            doc_type = item.get("doc_type", "document")
            faq_bonus = self.FAQ_BONUS if doc_type == "faq" else 0.0

            final_score = (
                self.vector_weight * vector_score
                + self.keyword_weight * keyword_score
                + self.length_weight * length_score
                + faq_bonus
            )

            # 限制在 [0, 1]
            final_score = max(0.0, min(1.0, final_score))

            ranked.append(
                RankedCandidate(
                    text=item.get("text", ""),
                    source=item.get("source", ""),
                    doc_type=doc_type,
                    chunk_index=item.get("chunk_index", 0),
                    vector_score=round(vector_score, 4),
                    keyword_score=round(keyword_score, 4),
                    final_score=round(final_score, 4),
                    answer=item.get("answer", ""),
                    metadata=item.get("metadata", {}),
                )
            )

        ranked.sort(key=lambda x: x.final_score, reverse=True)
        log.info(f"重排序完成: 输入 {len(candidates)} 条，输出 top-{top_k}")
        return ranked[:top_k]

    def _tokenize(self, text: str) -> list[str]:
        """
        中文分词（轻量级）

        策略：
        - 英文/数字：按单词提取
        - 中文：提取 2-gram 和 3-gram，兼顾召回率和计算量

        后续可替换为 jieba 等专业分词器
        """
        if not text:
            return []

        text = text.lower()
        # 英文和数字词
        tokens = re.findall(r"[a-z0-9]+", text)

        # 中文连续字符
        for chars in re.findall(r"[一-龥]+", text):
            if len(chars) < 2:
                continue
            # 2-gram
            for i in range(len(chars) - 1):
                tokens.append(chars[i : i + 2])
            # 3-gram
            if len(chars) >= 3:
                for i in range(len(chars) - 2):
                    tokens.append(chars[i : i + 3])

        return tokens

    def _keyword_score(self, query_tokens: list[str], text: str) -> float:
        """
        计算关键词匹配分数

        - 单个 token 命中：基础分
        - 连续多个 token 命中：额外奖励
        - 所有 token 都命中：完整匹配奖励
        """
        if not query_tokens:
            return 0.0

        text_lower = text.lower()
        matched = [t for t in query_tokens if t in text_lower]

        if not matched:
            return 0.0

        base_score = len(matched) / len(query_tokens)

        # 连续短语匹配奖励
        phrase_bonus = 0.0
        query_lower = " ".join(query_tokens)
        if query_lower in text_lower:
            phrase_bonus = 0.05
        elif all(t in text_lower for t in query_tokens):
            phrase_bonus = 0.03

        # 完整匹配奖励
        full_match_bonus = (
            self.KEYWORD_FULL_MATCH_BONUS if len(matched) == len(query_tokens) else 0.0
        )

        return min(1.0, base_score + phrase_bonus + full_match_bonus)

    def _length_score(self, text: str) -> float:
        """
        长度合理性打分

         preferred: 100-500 字符
        过短 (<50) 或过长 (>1000) 都会降权
        """
        length = len(text)

        if 100 <= length <= 500:
            return 1.0
        if length < 50:
            return 0.6
        if length > 1000:
            return 0.7
        # 50-100 或 500-1000 之间线性过渡
        if length < 100:
            return 0.6 + (length - 50) / 50 * 0.4
        return 1.0 - (length - 500) / 500 * 0.3


# 全局重排序器实例
reranker = Reranker()
