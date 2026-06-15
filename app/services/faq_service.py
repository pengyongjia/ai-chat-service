"""
FAQ 服务层
处理 FAQ 的增删改查、批量导入等操作
"""

from app.core.logging import log
from app.db.vector_store import vector_store
from app.models.faq import FAQBatchRequest, FAQItem


class FAQService:
    """FAQ 服务"""

    def seed(self, request: FAQBatchRequest) -> dict:
        """批量导入 FAQ，会清空原有数据"""
        if not request.faqs:
            raise ValueError("FAQ 列表不能为空")

        faqs = [f.model_dump() for f in request.faqs]

        vector_store.clear()
        vector_store.add_faqs(faqs)

        log.info(f"批量导入 {len(faqs)} 条 FAQ")

        return {
            "success": True,
            "count": len(faqs),
            "message": f"成功导入 {len(faqs)} 条 FAQ",
        }

    def add(self, item: FAQItem) -> dict:
        """单条添加 FAQ"""
        vector_store.add_faqs([item.model_dump()])
        log.info(f"新增 FAQ: {item.question[:30]}...")

        return {
            "success": True,
            "message": "添加成功",
        }

    def count(self) -> dict:
        """获取 FAQ 数量"""
        return {
            "count": vector_store.count(),
        }

    def clear(self) -> dict:
        """清空 FAQ"""
        vector_store.clear()
        log.warning("FAQ 向量库已清空")

        return {
            "success": True,
            "message": "已清空",
        }


# 全局 FAQ 服务实例
faq_service = FAQService()
