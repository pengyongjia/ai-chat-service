"""
聊天 API v1
"""

from fastapi import APIRouter

from app.core.exceptions import AppException
from app.core.logging import log
from app.core.responses import error_response, success_response
from app.models.chat import (
    ChatRequest,
    SessionClearRequest,
)
from app.services.chat_service import chat_service
from app.services.conversation_service import conversation_service

router = APIRouter(prefix="/chat", tags=["对话"])


@router.post("/ask")
async def ask(request: ChatRequest):
    """用户提问接口（支持多轮对话）"""
    try:
        result = chat_service.answer(request.question, session_id=request.session_id)
        # 返回 session_id，如果是新会话前端可以用它继续对话
        if request.session_id:
            result["session_id"] = request.session_id
        return success_response(data=result)
    except AppException as e:
        log.error(f"业务异常: {e.message}")
        return error_response(message=e.message, code=400)
    except Exception:
        log.exception("问答服务异常")
        return error_response(message="服务暂时不可用，请稍后重试", code=500)


@router.post("/sessions")
async def create_session():
    """创建新会话"""
    try:
        result = conversation_service.create_session()
        return success_response(data=result)
    except Exception:
        log.exception("创建会话异常")
        return error_response(message="创建会话失败", code=500)


@router.get("/sessions")
async def list_sessions():
    """列出所有会话"""
    try:
        sessions = conversation_service.list_sessions()
        return success_response(data={"total": len(sessions), "sessions": sessions})
    except Exception:
        log.exception("列会话异常")
        return error_response(message="获取会话列表失败", code=500)


@router.get("/history/{session_id}")
async def get_history(session_id: str):
    """获取会话历史"""
    try:
        messages = conversation_service.get_history(session_id)
        return success_response(
            data={
                "session_id": session_id,
                "messages": [m.__dict__ for m in messages],
                "total": len(messages),
            }
        )
    except Exception:
        log.exception("获取会话历史异常")
        return error_response(message="获取会话历史失败", code=500)


@router.post("/clear")
async def clear_session(request: SessionClearRequest):
    """清空会话历史"""
    try:
        success = conversation_service.clear_session(request.session_id)
        if not success:
            return error_response(message="会话不存在", code=404)
        return success_response(data={"success": True, "message": "会话已清空"})
    except Exception:
        log.exception("清空会话异常")
        return error_response(message="清空会话失败", code=500)


@router.delete("/sessions/{session_id}")
async def delete_session(session_id: str):
    """删除会话"""
    try:
        success = conversation_service.delete_session(session_id)
        if not success:
            return error_response(message="会话不存在", code=404)
        return success_response(data={"success": True, "message": "会话已删除"})
    except Exception:
        log.exception("删除会话异常")
        return error_response(message="删除会话失败", code=500)


@router.get("/health")
async def health():
    """服务健康检查"""
    return success_response(data={"status": "ok"})
