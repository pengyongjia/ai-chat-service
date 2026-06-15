"""
知识库服务层
处理文档上传、切分、存储、删除等操作
"""

import json
import shutil
from datetime import datetime
from pathlib import Path

from app.config import config
from app.core.document_loader import DocumentLoaderError, document_loader
from app.core.exceptions import VectorStoreError
from app.core.logging import log
from app.core.text_splitter import text_splitter
from app.db.vector_store import Chunk, vector_store

# 上传文件保存目录
UPLOAD_DIR = Path("knowledge/uploads")
# 文档元数据文件
METADATA_FILE = Path("knowledge/documents.json")


class KnowledgeService:
    """知识库服务"""

    def __init__(self):
        self.upload_dir = UPLOAD_DIR
        self.metadata_file = METADATA_FILE
        self.upload_dir.mkdir(parents=True, exist_ok=True)

    def _load_metadata(self) -> list[dict]:
        """加载文档元数据"""
        if not self.metadata_file.exists():
            return []
        try:
            return json.loads(self.metadata_file.read_text(encoding="utf-8"))
        except Exception as e:
            log.warning(f"加载文档元数据失败: {e}")
            return []

    def _save_metadata(self, metadata: list[dict]):
        """保存文档元数据"""
        self.metadata_file.parent.mkdir(parents=True, exist_ok=True)
        self.metadata_file.write_text(
            json.dumps(metadata, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def process_upload(self, filename: str, file_content: bytes) -> dict:
        """
        处理上传的文档

        Args:
            filename: 原始文件名
            file_content: 文件二进制内容

        Returns:
            处理结果
        """
        # 安全处理文件名
        safe_filename = Path(filename).name
        suffix = Path(safe_filename).suffix.lower()

        if suffix not in [".pdf", ".docx", ".doc", ".xlsx", ".xls", ".csv", ".md", ".txt"]:
            raise DocumentLoaderError(f"不支持的文件格式: {suffix}")

        # 保存上传文件
        file_path = self.upload_dir / safe_filename
        file_path.write_bytes(file_content)

        # 加载文本
        text = document_loader.load(str(file_path))

        if not text or not text.strip():
            raise DocumentLoaderError("文档内容为空，无法处理")

        # 根据文件类型选择切分策略
        if suffix in [".md", ".markdown"]:
            chunks = text_splitter.split_by_markdown_headers(text, source=safe_filename)
        else:
            chunks = text_splitter.split(text, source=safe_filename)

        # 设置 doc_type
        for chunk in chunks:
            chunk.doc_type = "document"

        # 存储到向量库
        vector_store.add_chunks(chunks)

        # 更新元数据
        metadata = self._load_metadata()
        # 如果已存在同名文件，先移除旧记录
        metadata = [m for m in metadata if m["filename"] != safe_filename]
        metadata.append(
            {
                "filename": safe_filename,
                "doc_type": suffix.lstrip("."),
                "chunk_count": len(chunks),
                "uploaded_at": datetime.now().isoformat(),
            }
        )
        self._save_metadata(metadata)

        log.info(f"文档上传成功: {safe_filename}, 生成 {len(chunks)} 个 chunks")

        return {
            "success": True,
            "filename": safe_filename,
            "doc_type": suffix.lstrip("."),
            "chunk_count": len(chunks),
            "message": f"成功上传 {safe_filename}，生成 {len(chunks)} 个知识片段",
        }

    def list_documents(self) -> dict:
        """列出已上传文档"""
        metadata = self._load_metadata()
        return {
            "total": len(metadata),
            "items": metadata,
        }

    def delete_document(self, filename: str) -> dict:
        """
        删除文档
        注意：当前实现会清空所有 document 类型的 chunks，然后重新上传剩余文档
        这是简化实现，后续可以优化为按文件精确删除
        """
        metadata = self._load_metadata()
        doc = next((m for m in metadata if m["filename"] == filename), None)

        if not doc:
            raise DocumentLoaderError(f"文档不存在: {filename}")

        # 删除上传文件
        file_path = self.upload_dir / filename
        if file_path.exists():
            file_path.unlink()

        # 从元数据中移除
        metadata = [m for m in metadata if m["filename"] != filename]
        self._save_metadata(metadata)

        # 清空所有 document chunks，然后重新上传剩余文档
        # 这是一个简化实现，精确删除需要向量库支持按 source 删除
        vector_store.clear(doc_type="document")

        # 重新处理剩余文档
        for item in metadata:
            remaining_path = self.upload_dir / item["filename"]
            if remaining_path.exists():
                try:
                    text = document_loader.load(str(remaining_path))
                    suffix = remaining_path.suffix.lower()
                    if suffix in [".md", ".markdown"]:
                        chunks = text_splitter.split_by_markdown_headers(
                            text, source=item["filename"]
                        )
                    else:
                        chunks = text_splitter.split(text, source=item["filename"])
                    for chunk in chunks:
                        chunk.doc_type = "document"
                    vector_store.add_chunks(chunks)
                except Exception as e:
                    log.error(f"重新处理文档失败 {item['filename']}: {e}")

        log.info(f"文档已删除: {filename}")

        return {
            "success": True,
            "message": f"已删除 {filename}",
        }

    def get_stats(self) -> dict:
        """获取知识库统计"""
        try:
            faq_count = vector_store.count(doc_type="faq")
            document_count = vector_store.count(doc_type="document")
        except Exception:
            faq_count = 0
            document_count = 0

        metadata = self._load_metadata()

        return {
            "faq_count": faq_count,
            "document_count": document_count,
            "total_count": faq_count + document_count,
            "files": metadata,
        }

    def clear_all_documents(self) -> dict:
        """清空所有文档（保留 FAQ）"""
        vector_store.clear(doc_type="document")

        # 删除上传文件
        if self.upload_dir.exists():
            shutil.rmtree(self.upload_dir)
            self.upload_dir.mkdir(parents=True, exist_ok=True)

        # 清空元数据
        self._save_metadata([])

        log.warning("所有文档已清空")

        return {
            "success": True,
            "message": "已清空所有文档",
        }


# 全局知识库服务实例
knowledge_service = KnowledgeService()
