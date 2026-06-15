"""
聊天相关 Pydantic 模型
"""

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    """聊天请求"""

    question: str = Field(
        ...,
        min_length=1,
        max_length=2000,
        description="用户问题",
    )
    session_id: str | None = Field(
        default=None,
        description="会话 ID（可选，用于多轮对话）",
    )


class ChatResponse(BaseModel):
    """聊天响应"""

    answer: str = Field(..., description="AI 回答")
    source: str = Field(..., description="回答来源：faq / llm / reject")
    confidence: float = Field(default=0.0, description="匹配置信度")
    matched_question: str = Field(default="", description="匹配到的问题")
    references: list = Field(default_factory=list, description="参考来源列表")
