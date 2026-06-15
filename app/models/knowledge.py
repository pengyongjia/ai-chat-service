"""
文档知识库相关 Pydantic 模型
"""

from pydantic import BaseModel, Field


class KnowledgeUploadResponse(BaseModel):
    """文档上传响应"""

    success: bool = Field(..., description="是否成功")
    filename: str = Field(..., description="文件名")
    doc_type: str = Field(..., description="文档类型")
    chunk_count: int = Field(..., description="切分出的 chunk 数量")
    message: str = Field(..., description="提示信息")


class KnowledgeItem(BaseModel):
    """知识库中的文档项"""

    filename: str = Field(..., description="文件名")
    doc_type: str = Field(..., description="文档类型")
    chunk_count: int = Field(..., description="chunk 数量")
    uploaded_at: str = Field(..., description="上传时间")


class KnowledgeListResponse(BaseModel):
    """文档列表响应"""

    total: int = Field(..., description="总数")
    items: list[KnowledgeItem] = Field(..., description="文档列表")


class KnowledgeDeleteRequest(BaseModel):
    """删除文档请求"""

    filename: str = Field(..., min_length=1, description="要删除的文件名")


class KnowledgeStatsResponse(BaseModel):
    """知识库统计响应"""

    faq_count: int = Field(..., description="FAQ 数量")
    document_count: int = Field(..., description="文档 chunk 数量")
    total_count: int = Field(..., description="总知识条目数")
    files: list[KnowledgeItem] = Field(..., description="已上传文件列表")
