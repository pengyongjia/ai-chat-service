"""
FAQ 相关 Pydantic 模型
"""

from pydantic import BaseModel, Field


class FAQItem(BaseModel):
    """单条 FAQ"""

    question: str = Field(..., min_length=1, max_length=500, description="问题")
    answer: str = Field(..., min_length=1, max_length=5000, description="答案")


class FAQBatchRequest(BaseModel):
    """批量 FAQ 请求"""

    faqs: list[FAQItem] = Field(..., min_length=1, description="FAQ 列表")


class FAQCountResponse(BaseModel):
    """FAQ 数量响应"""

    count: int = Field(..., description="FAQ 数量")
