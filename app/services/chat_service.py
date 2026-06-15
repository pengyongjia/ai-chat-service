"""
聊天服务层
实现 RAG 三级兜底策略：
  1. 高置信命中 → 直接返回答案
  2. 半相关 → 调用 LLM 基于上下文生成
  3. 不相关 → 拒绝回答，引导人工
"""

from openai import OpenAI

from app.config import config
from app.core.exceptions import LLMError
from app.core.logging import log
from app.db.vector_store import vector_store


class ChatService:
    """聊天服务"""

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

        # 1. 检索 Top-K FAQ
        results = vector_store.search(question, top_k=config.FAQ_TOP_K)

        # 2. 解析结果
        matches = self._parse_results(results)

        # 3. 高置信命中 → 直接回答
        if matches and matches[0]["similarity"] >= config.FAQ_THRESHOLD_HIGH:
            log.info(f"直接命中 FAQ，相似度: {matches[0]['similarity']}")
            return {
                "source": "faq",
                "answer": matches[0]["answer"],
                "matched_question": matches[0]["question"],
                "confidence": matches[0]["similarity"],
                "references": [],
            }

        # 4. 不相关 → 直接拒绝，避免幻觉
        if not matches or matches[0]["similarity"] < config.FAQ_THRESHOLD_LOW:
            log.info(f"相似度过低，拒绝回答: {matches[0]['similarity'] if matches else 0}")
            return {
                "source": "reject",
                "answer": "抱歉，这个问题超出了我的知识范围。您可以点击页面右下角的【立即体验】提交表单，我们的专业顾问将在 24 小时内为您详细解答。",
                "matched_question": matches[0]["question"] if matches else "",
                "confidence": matches[0]["similarity"] if matches else 0.0,
                "references": [],
            }

        # 5. 半相关 → 调用 DeepSeek 基于上下文生成
        return self._generate_by_llm(question, matches)

    def _parse_results(self, results: dict) -> list[dict]:
        """解析向量检索结果"""
        matches = []
        if results.get("distances") and results["distances"][0]:
            for i in range(len(results["distances"][0])):
                distance = results["distances"][0][i]
                similarity = 1 - distance  # cosine 距离转相似度
                matches.append(
                    {
                        "question": results["metadatas"][0][i]["question"],
                        "answer": results["metadatas"][0][i]["answer"],
                        "similarity": round(similarity, 4),
                    }
                )
        return matches

    def _generate_by_llm(self, question: str, matches: list[dict]) -> dict:
        """基于上下文调用 LLM 生成回答"""
        context_blocks = [f"Q: {m['question']}\nA: {m['answer']}" for m in matches]
        context_str = "\n\n".join(context_blocks)

        system_prompt = f"""你是"应有成本估算系统"的智能助手，专注于离散制造业成本管理领域。

请严格基于以下知识库内容回答用户问题。如果知识库中没有直接答案，请基于已有信息进行合理推断，但不要编造知识库之外的内容。
---
{context_str}
---

回答规则：
1. 知识库中有直接答案 → 直接引用
2. 知识库中无直接答案但有关联信息 → 基于关联信息合理推断，明确说明"根据我们的经验..."
3. 完全无法回答 → 建议联系人工客服
4. 回答控制在 200 字以内，简洁专业
"""

        try:
            response = self.client.chat.completions.create(
                model=config.DEEPSEEK_MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": question},
                ],
                temperature=0.3,
                max_tokens=500,
            )

            answer = response.choices[0].message.content
            log.info("LLM 兜底生成回答完成")

            return {
                "source": "llm",
                "answer": answer,
                "confidence": matches[0]["similarity"],
                "matched_question": "",
                "references": [
                    {"q": m["question"], "similarity": m["similarity"]} for m in matches
                ],
            }
        except Exception as e:
            log.error(f"LLM 调用失败: {e}")
            raise LLMError(f"大模型调用失败: {e}")


# 全局聊天服务实例
chat_service = ChatService()
