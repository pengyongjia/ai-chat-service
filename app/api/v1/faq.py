"""
FAQ 管理 API v1
"""

from fastapi import APIRouter, HTTPException

from app.core.logging import log
from app.core.responses import error_response, success_response
from app.models.faq import FAQBatchRequest, FAQCountResponse, FAQItem
from app.services.faq_service import faq_service

router = APIRouter(prefix="/faq", tags=["FAQ 管理"])


@router.post("/seed")
async def seed_faqs(request: FAQBatchRequest):
    """批量导入 FAQ 到向量库（会先清空原有数据）"""
    try:
        result = faq_service.seed(request)
        return success_response(data=result, message=result["message"])
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        log.exception("FAQ 批量导入失败")
        return error_response(message=f"导入失败: {str(e)}", code=500)


@router.post("/add")
async def add_faq(item: FAQItem):
    """单条添加 FAQ"""
    try:
        result = faq_service.add(item)
        return success_response(data=result, message=result["message"])
    except Exception as e:
        log.exception("FAQ 添加失败")
        return error_response(message=f"添加失败: {str(e)}", code=500)


@router.get("/count", response_model=FAQCountResponse)
async def get_count():
    """获取 FAQ 数量"""
    return faq_service.count()


@router.post("/clear")
async def clear_faqs():
    """清空向量库"""
    try:
        result = faq_service.clear()
        return success_response(data=result, message=result["message"])
    except Exception as e:
        log.exception("FAQ 清空失败")
        return error_response(message=f"清空失败: {str(e)}", code=500)
