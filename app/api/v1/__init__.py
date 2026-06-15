"""
API v1 路由聚合
"""

from fastapi import APIRouter

from app.api.v1.chat import router as chat_router
from app.api.v1.faq import router as faq_router

api_router = APIRouter(prefix="/v1")

api_router.include_router(chat_router)
api_router.include_router(faq_router)
