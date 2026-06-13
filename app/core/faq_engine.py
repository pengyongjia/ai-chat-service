from openai import OpenAI

from app.config import config
from app.core.vector_store import vector_store


class FAQEngine:
    def __init__(self):
        self.client = OpenAI(
            api_key=config.DEEPSEEK_API_KEY,
            base_url=config.DEEPSEEK_BASE_URL
        )

    def answer(self, question: str) -> dict:
        """
        FAQ 问答主流程（三级兜底策略）：
        1. 检索 Top-K FAQ，计算相似度
        2. 高置信命中 (>= 0.75) → 直接返回答案
        3. 半相关 (0.50 ~ 0.74) → 调用 DeepSeek 基于上下文生成
        4. 不相关 (< 0.50) → 直接拒绝，引导提交表单
        """
        # 1. 检索
        results = vector_store.search(question, top_k=config.FAQ_TOP_K)

        # 2. 解析结果
        matches = []
        if results.get("distances") and results["distances"][0]:
            for i in range(len(results["distances"][0])):
                distance = results["distances"][0][i]
                similarity = 1 - distance  # cosine 距离转相似度
                matches.append({
                    "question": results["metadatas"][0][i]["question"],
                    "answer": results["metadatas"][0][i]["answer"],
                    "similarity": round(similarity, 4)
                })

        # 3. 高置信命中 → 直接回答
        if matches and matches[0]["similarity"] >= config.FAQ_THRESHOLD_HIGH:
            return {
                "source": "faq",
                "answer": matches[0]["answer"],
                "matched_question": matches[0]["question"],
                "confidence": matches[0]["similarity"]
            }

        # 4. 不相关 → 直接拒绝，避免幻觉
        if not matches or matches[0]["similarity"] < config.FAQ_THRESHOLD_LOW:
            return {
                "source": "reject",
                "answer": "抱歉，这个问题超出了我的知识范围。您可以点击页面右下角的【立即体验】提交表单，我们的专业顾问将在 24 小时内为您详细解答。",
                "matched_question": matches[0]["question"] if matches else "",
                "confidence": matches[0]["similarity"] if matches else 0.0
            }

        # 5. 半相关 (0.50 ~ 0.74) → 调用 DeepSeek 基于上下文生成
        context_blocks = []
        for m in matches:
            context_blocks.append(f"Q: {m['question']}\nA: {m['answer']}")

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
                    {"role": "user", "content": question}
                ],
                temperature=0.3,
                max_tokens=500
            )

            return {
                "source": "llm",
                "answer": response.choices[0].message.content,
                "confidence": matches[0]["similarity"],
                "references": [{"q": m["question"], "similarity": m["similarity"]} for m in matches]
            }
        except Exception as e:
            return {
                "source": "error",
                "answer": "服务暂时不可用，请稍后重试。您也可以点击【立即体验】提交表单联系客服。",
                "confidence": 0.0
            }


faq_engine = FAQEngine()
