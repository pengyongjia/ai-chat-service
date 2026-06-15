"""
聊天 API v1
"""

from fastapi import APIRouter

from app.core.exceptions import AppException
from app.core.logging import log
from app.core.responses import error_response, success_response
from app.models.chat import ChatRequest
from app.services.chat_service import chat_service

router = APIRouter(prefix="/chat", tags=["对话"])


@router.post("/ask")
async def ask(request: ChatRequest):
    """用户提问接口"""
    try:
        result = chat_service.answer(request.question)
        return success_response(data=result)
    except AppException as e:
        log.error(f"业务异常: {e.message}")
        return error_response(message=e.message, code=400)
    except Exception as e:
        log.exception("问答服务异常")
        return error_response(message="服务暂时不可用，请稍后重试", code=500)


@router.get("/health")
async def health():
    """服务健康检查"""
    return success_response(data={"status": "ok"})
