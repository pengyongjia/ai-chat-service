"""
上下文压缩模块
对检索到的候选 chunks 进行过滤和压缩，控制进入 LLM 的上下文质量
"""

from app.config import config
from app.core.logging import log
from app.services.llm_client import LLMClient


class ContextCompressor:
    """
    上下文压缩器

    策略：
    1. 阈值过滤：丢弃相似度低于阈值的候选
    2. 长度截断：对超长 chunk 进行尾部截断
    3. LLM 压缩（可选）：调用 LLM 对 chunk 进行摘要，保留与问题相关的信息
    """

    def __init__(
        self,
        similarity_threshold: float = 0.35,
        max_chunk_length: int = 600,
        enable_llm_compress: bool = False,
    ):
        self.similarity_threshold = similarity_threshold
        self.max_chunk_length = max_chunk_length
        self.enable_llm_compress = enable_llm_compress
        self._llm_client: LLMClient | None = None

    def compress(
        self, query: str, candidates: list[dict], max_total_length: int = 2500
    ) -> list[dict]:
        """
        压缩候选上下文

        Args:
            query: 用户查询
            candidates: 候选结果列表
            max_total_length: 压缩后总长度上限

        Returns:
            压缩后的候选列表
        """
        if not candidates:
            return []

        # 1. 按相似度阈值过滤
        filtered = [c for c in candidates if c.get("similarity", 0.0) >= self.similarity_threshold]
        if not filtered:
            # 如果全部都被过滤，保留最优一条，避免完全无上下文
            filtered = sorted(candidates, key=lambda x: x.get("similarity", 0.0), reverse=True)[:1]

        # 2. 长度截断 + LLM 压缩
        compressed = []
        total_length = 0
        for candidate in filtered:
            text = candidate.get("text", "")

            if self.enable_llm_compress and len(text) > self.max_chunk_length:
                text = self._llm_compress(query, text)
            elif len(text) > self.max_chunk_length:
                text = text[: self.max_chunk_length] + "..."

            new_candidate = {**candidate, "text": text}
            if total_length + len(text) > max_total_length:
                break

            compressed.append(new_candidate)
            total_length += len(text)

        log.info(f"上下文压缩: {len(candidates)} -> {len(compressed)} 条")
        return compressed

    def _llm_compress(self, query: str, text: str) -> str:
        """
        调用 LLM 对文本进行问题相关的摘要压缩

        注意：会消耗额外 token，建议在长文档场景下开启
        """
        if self._llm_client is None:
            self._llm_client = LLMClient()

        prompt = f"""请根据用户问题，从以下参考资料中提取最相关的信息，删除无关内容，保持简洁。

用户问题：{query}

参考资料：
{text}

请只输出与问题相关的内容，控制在 200 字以内："""

        try:
            compressed = self._llm_client.complete(
                prompt=prompt,
                temperature=0.2,
                max_tokens=300,
            )
            return compressed.strip() or text
        except Exception as e:
            log.warning(f"LLM 压缩失败，使用截断: {e}")
            return text[: self.max_chunk_length] + "..."


# 全局上下文压缩器实例
context_compressor = ContextCompressor(
    similarity_threshold=config.CONTEXT_SIMILARITY_THRESHOLD,
    max_chunk_length=config.CONTEXT_MAX_CHUNK_LENGTH,
    enable_llm_compress=config.ENABLE_LLM_CONTEXT_COMPRESS,
)
