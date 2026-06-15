"""
查询重写模块
将用户口语化、不完整的查询改写为更适合向量检索的标准查询
"""

import json

from app.config import config
from app.core.exceptions import LLMError
from app.core.logging import log
from app.services.llm_client import llm_client


class QueryRewriter:
    """
    查询重写器

    功能：
    1. 纠错：修正错别字、口语化表达
    2. 扩展：生成同义/近义查询变体
    3. 标准化：将问题改写成更贴近知识库文本的表述
    """

    def __init__(self, enabled: bool = True):
        self.enabled = enabled

    def rewrite(self, query: str) -> str:
        """
        改写单个查询

        Args:
            query: 原始用户问题

        Returns:
            改写后的标准查询，如果关闭或失败则返回原查询
        """
        if not self.enabled or not query or not query.strip():
            return query

        try:
            prompt = self._build_rewrite_prompt(query)
            rewritten = llm_client.complete(
                prompt=prompt,
                temperature=0.2,
                max_tokens=200,
            )
            cleaned = rewritten.strip().strip('"').strip("'")
            if cleaned and len(cleaned) >= len(query) * 0.5:
                log.info(f"查询重写: '{query[:40]}...' -> '{cleaned[:40]}...'")
                return cleaned
            return query
        except LLMError:
            log.warning("查询重写失败，使用原查询")
            return query
        except Exception as e:
            log.warning(f"查询重写异常: {e}")
            return query

    def expand(self, query: str, n: int = 2) -> list[str]:
        """
        生成多个查询扩展变体

        Args:
            query: 原始查询
            n: 生成变体数量

        Returns:
            查询变体列表（包含原查询）
        """
        if not self.enabled or not query or not query.strip():
            return [query]

        try:
            prompt = self._build_expand_prompt(query, n)
            response = llm_client.complete(
                prompt=prompt,
                temperature=0.4,
                max_tokens=300,
            )
            variants = self._parse_variants(response)
            # 确保原查询在第一位
            if query not in variants:
                variants.insert(0, query)
            else:
                variants.remove(query)
                variants.insert(0, query)
            log.info(f"查询扩展: 生成 {len(variants)} 个变体")
            return variants[: n + 1]
        except Exception as e:
            log.warning(f"查询扩展失败: {e}")
            return [query]

    def _build_rewrite_prompt(self, query: str) -> str:
        return f"""你是一位搜索优化专家。请将用户的问题改写成一个简洁、标准、更适合语义检索的查询。

要求：
1. 保留用户的核心意图和关键实体（产品名、功能、问题类型等）
2. 修正错别字和口语化表达
3. 输出必须是一个完整的问句或短语
4. 不要添加解释，只输出改写后的查询

用户问题：{query}

改写后的查询："""

    def _build_expand_prompt(self, query: str, n: int) -> str:
        return f"""你是一位搜索优化专家。请为以下查询生成 {n} 个语义相同或近似的表达变体，用于提升检索召回率。

要求：
1. 变体必须与原查询意思一致
2. 使用不同的措辞、句式或同义词
3. 输出必须是 JSON 数组格式，例如：["变体1", "变体2"]
4. 不要添加任何解释

查询：{query}

JSON 数组："""

    def _parse_variants(self, response: str) -> list[str]:
        """解析 LLM 返回的变体列表"""
        try:
            # 尝试直接解析 JSON
            data = json.loads(response.strip())
            if isinstance(data, list):
                return [str(v).strip() for v in data if v and str(v).strip()]
        except json.JSONDecodeError:
            pass

        # 兜底：按行解析
        variants = []
        for line in response.split("\n"):
            line = line.strip().strip('",[]{}')
            if line and len(line) >= 4:
                variants.append(line)
        return variants


# 全局查询重写器实例
query_rewriter = QueryRewriter(enabled=config.ENABLE_QUERY_REWRITE)
