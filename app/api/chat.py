from fastapi import APIRouter
from pydantic import BaseModel

from app.core.faq_engine import faq_engine

router = APIRouter(prefix="/chat", tags=["对话"])


class ChatRequest(BaseModel):
    question: str


class ChatResponse(BaseModel):
    answer: str
    source: str
    confidence: float
    matched_question: str = ""
    references: list = []


@router.post("/ask", response_model=ChatResponse)
async def ask(request: ChatRequest):
    """用户提问接口"""
    result = faq_engine.answer(request.question)

    return ChatResponse(
        answer=result["answer"],
        source=result["source"],
        confidence=result.get("confidence", 0.0),
        matched_question=result.get("matched_question", ""),
        references=result.get("references", [])
    )


@router.get("/health")
async def health():
    """服务健康检查"""
    return {"status": "ok"}
