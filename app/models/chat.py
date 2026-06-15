"""
聊天相关 Pydantic 模型
"""

from datetime import datetime

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
    session_id: str | None = Field(default=None, description="会话 ID")


class ChatStreamRequest(BaseModel):
    """流式聊天请求"""

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


class ChatStreamEvent(BaseModel):
    """SSE 流式事件"""

    type: str = Field(..., description="事件类型：start / chunk / done / error")
    content: str | None = Field(default=None, description="文本片段内容")
    answer: str | None = Field(default=None, description="完整回答（done 事件）")
    source: str | None = Field(default=None, description="回答来源（done 事件）")
    confidence: float | None = Field(default=None, description="置信度（done 事件）")
    matched_question: str | None = Field(default="", description="匹配到的问题（done 事件）")
    references: list | None = Field(default_factory=list, description="参考来源（done 事件）")
    message: str | None = Field(default=None, description="错误信息（error 事件）")
    code: str | None = Field(default=None, description="错误码（error 事件）")


class ChatMessage(BaseModel):
    """单条聊天消息"""

    role: str = Field(..., description="消息角色：user / assistant / system")
    content: str = Field(..., description="消息内容")
    timestamp: datetime = Field(default_factory=datetime.now, description="消息时间")


class SessionCreateResponse(BaseModel):
    """创建会话响应"""

    session_id: str = Field(..., description="会话 ID")
    created_at: datetime = Field(..., description="创建时间")


class SessionHistoryResponse(BaseModel):
    """会话历史响应"""

    session_id: str = Field(..., description="会话 ID")
    messages: list[ChatMessage] = Field(default_factory=list, description="历史消息")
    total: int = Field(default=0, description="消息总数")


class SessionClearRequest(BaseModel):
    """清空会话请求"""

    session_id: str = Field(..., min_length=1, description="会话 ID")


class SessionListResponse(BaseModel):
    """会话列表响应"""

    total: int = Field(default=0, description="会话总数")
    sessions: list[dict] = Field(default_factory=list, description="会话列表")
