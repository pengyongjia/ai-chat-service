"""
健康检查 API
提供服务和依赖组件的健康状态
"""

from fastapi import APIRouter

from app.config import config
from app.core.responses import success_response
from app.db.vector_store import vector_store

router = APIRouter(prefix="/health", tags=["健康检查"])


@router.get("")
async def health_check():
    """基础健康检查"""
    return success_response(
        data={
            "status": "healthy",
            "service": config.APP_NAME,
            "version": config.APP_VERSION,
            "env": config.APP_ENV,
        }
    )


@router.get("/ready")
async def readiness_check():
    """就绪检查：包含依赖组件状态"""
    checks = {
        "vector_store": _check_vector_store(),
    }

    all_healthy = all(checks.values())

    return success_response(
        data={
            "status": "ready" if all_healthy else "not_ready",
            "checks": checks,
        }
    )


def _check_vector_store() -> bool:
    """检查向量存储是否可用"""
    try:
        vector_store.count()
        return True
    except Exception:
        return False
