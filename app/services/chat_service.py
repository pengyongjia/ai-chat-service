"""
聊天服务层
实现 RAG 三级兜底策略，支持 FAQ + 文档 chunks 混合检索
"""

from openai import OpenAI

from app.config import config
from app.core.exceptions import LLMError
from app.core.logging import log
from app.db.vector_store import vector_store


class ChatService:
    """聊天服务"""

    # 最大上下文长度（字符数）
    MAX_CONTEXT_LENGTH = 2500

    def __init__(self):
        self._client = None

    @property
    def client(self):
        """延迟初始化 OpenAI 客户端"""
        if self._client is None:
            self._client = OpenAI(
                api_key=config.DEEPSEEK_API_KEY,
                base_url=config.DEEPSEEK_BASE_URL,
            )
        return self._client

    def answer(self, question: str) -> dict:
        """
        用户提问主流程
        """
        log.info(f"收到用户提问: {question[:50]}...")

        # 1. 检索 Top-K 相关知识（FAQ + 文档 chunks）
        results = vector_store.search(
            question,
            top_k=config.FAQ_TOP_K + 3,  # 多检索一些，后续合并处理
            doc_types=["faq", "document"],
        )

        # 2. 解析结果
        matches = self._parse_results(results)

        if not matches:
            return self._reject(question="", confidence=0.0)

        # 3. 高置信命中 FAQ → 直接回答
        top_match = matches[0]
        if top_match["doc_type"] == "faq" and top_match["similarity"] >= config.FAQ_THRESHOLD_HIGH:
            log.info(f"直接命中 FAQ，相似度: {top_match['similarity']}")
            return {
                "source": "faq",
                "answer": top_match["answer"],
                "matched_question": top_match["text"],
                "confidence": top_match["similarity"],
                "references": [],
            }

        # 4. 不相关 → 直接拒绝，避免幻觉
        if top_match["similarity"] < config.FAQ_THRESHOLD_LOW:
            log.info(f"相似度过低，拒绝回答: {top_match['similarity']}")
            return self._reject(
                question=top_match["text"],
                confidence=top_match["similarity"],
            )

        # 5. 半相关 → 基于检索到的知识生成回答
        return self._generate_by_llm(question, matches)

    def _parse_results(self, results: dict) -> list[dict]:
        """解析向量检索结果，统一格式"""
        matches = []

        if not results.get("distances") or not results["distances"][0]:
            return matches

        for i in range(len(results["distances"][0])):
            distance = results["distances"][0][i]
            similarity = 1 - distance  # cosine 距离转相似度
            metadata = results["metadatas"][0][i]

            matches.append(
                {
                    "text": metadata.get("text", ""),
                    "answer": metadata.get("answer", ""),
                    "source": metadata.get("source", ""),
                    "doc_type": metadata.get("doc_type", "document"),
                    "chunk_index": metadata.get("chunk_index", 0),
                    "similarity": round(similarity, 4),
                    "metadata": metadata,
                }
            )

        # 按相似度排序（保险起见）
        matches.sort(key=lambda x: x["similarity"], reverse=True)
        return matches

    def _generate_by_llm(self, question: str, matches: list[dict]) -> dict:
        """基于上下文调用 LLM 生成回答"""
        # 构建上下文，控制长度
        context_blocks, references = self._build_context(matches)
        context_str = "\n\n---\n\n".join(context_blocks)

        system_prompt = f"""你是专业、严谨的智能助手。请严格基于以下参考资料回答用户问题。

参考资料：
---
{context_str}
---

回答规则：
1. 如果参考资料中有直接答案，请直接引用并清晰回答。
2. 如果参考资料中没有直接答案，但有关联信息，请基于关联信息合理推断，并明确说明"根据参考资料..."
3. 如果完全无法从参考资料中得出答案，请明确说明"根据现有资料无法回答该问题"。
4. 不要编造参考资料之外的内容。
5. 回答控制在 300 字以内，简洁专业。
"""

        try:
            response = self.client.chat.completions.create(
                model=config.DEEPSEEK_MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": question},
                ],
                temperature=0.3,
                max_tokens=600,
            )

            answer = response.choices[0].message.content
            log.info("LLM 基于知识库生成回答完成")

            return {
                "source": "llm",
                "answer": answer,
                "confidence": matches[0]["similarity"],
                "matched_question": "",
                "references": references,
            }
        except Exception as e:
            log.error(f"LLM 调用失败: {e}")
            raise LLMError(f"大模型调用失败: {e}")

    def _build_context(self, matches: list[dict]) -> tuple[list[str], list[dict]]:
        """
        构建 LLM 上下文
        优先使用 FAQ，其次使用文档 chunks，控制总长度
        """
        context_blocks = []
        references = []
        total_length = 0

        for match in matches:
            if match["doc_type"] == "faq":
                block = f"Q: {match['text']}\nA: {match['answer']}"
            else:
                block = f"【来源：{match['source']}】\n{match['text']}"

            if total_length + len(block) > self.MAX_CONTEXT_LENGTH:
                break

            context_blocks.append(block)
            total_length += len(block)

            # 构建参考来源
            ref = {
                "source": match["source"],
                "doc_type": match["doc_type"],
                "similarity": match["similarity"],
            }
            if ref not in references:
                references.append(ref)

            # FAQ 命中时，通常一条就够了
            if match["doc_type"] == "faq" and match["similarity"] >= config.FAQ_THRESHOLD_HIGH:
                break

        return context_blocks, references

    def _reject(self, question: str, confidence: float) -> dict:
        """拒绝回答"""
        return {
            "source": "reject",
            "answer": "抱歉，这个问题超出了我的知识范围。您可以点击页面右下角的【立即体验】提交表单，我们的专业顾问将在 24 小时内为您详细解答。",
            "matched_question": question,
            "confidence": confidence,
            "references": [],
        }


# 全局聊天服务实例
chat_service = ChatService()
