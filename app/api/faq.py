from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.core.vector_store import vector_store

router = APIRouter(prefix="/faq", tags=["FAQ 管理"])


class FAQItem(BaseModel):
    question: str
    answer: str


class FAQBatchRequest(BaseModel):
    faqs: list[FAQItem]


@router.post("/seed")
async def seed_faqs(request: FAQBatchRequest):
    """
    批量导入 FAQ 到向量库
    会先清空原有数据，再重新导入
    """
    if not request.faqs:
        raise HTTPException(status_code=400, detail="FAQ 列表不能为空")

    vector_store.clear()
    vector_store.add_faqs([f.model_dump() for f in request.faqs])

    return {
        "success": True,
        "count": len(request.faqs),
        "message": f"成功导入 {len(request.faqs)} 条 FAQ"
    }


@router.post("/add")
async def add_faq(item: FAQItem):
    """单条添加 FAQ"""
    vector_store.add_faqs([item.model_dump()])
    return {"success": True, "message": "添加成功"}


@router.get("/count")
async def get_count():
    """获取 FAQ 数量"""
    return {"count": vector_store.count()}


@router.post("/clear")
async def clear_faqs():
    """清空向量库"""
    vector_store.clear()
    return {"success": True, "message": "已清空"}
