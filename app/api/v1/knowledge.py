"""
知识库管理 API v1
处理文档上传、列表、删除、统计等
"""

from fastapi import APIRouter, File, HTTPException, UploadFile

from app.core.logging import log
from app.core.responses import error_response, success_response
from app.models.knowledge import KnowledgeDeleteRequest
from app.services.knowledge_service import knowledge_service

router = APIRouter(prefix="/knowledge", tags=["知识库管理"])


@router.post("/upload")
async def upload_document(file: UploadFile = File(...)):
    """上传文档到知识库"""
    try:
        content = await file.read()
        result = knowledge_service.process_upload(file.filename, content)
        return success_response(data=result, message=result["message"])
    except Exception as e:
        log.exception(f"文档上传失败: {file.filename}")
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/list")
async def list_documents():
    """列出已上传文档"""
    result = knowledge_service.list_documents()
    return success_response(data=result)


@router.post("/delete")
async def delete_document(request: KnowledgeDeleteRequest):
    """删除指定文档"""
    try:
        result = knowledge_service.delete_document(request.filename)
        return success_response(data=result, message=result["message"])
    except Exception as e:
        log.exception(f"文档删除失败: {request.filename}")
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/stats")
async def knowledge_stats():
    """知识库统计"""
    result = knowledge_service.get_stats()
    return success_response(data=result)


@router.post("/clear-documents")
async def clear_documents():
    """清空所有文档（保留 FAQ）"""
    try:
        result = knowledge_service.clear_all_documents()
        return success_response(data=result, message=result["message"])
    except Exception as e:
        log.exception("清空文档失败")
        raise HTTPException(status_code=500, detail=str(e))
