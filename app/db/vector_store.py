"""
向量数据库存储层
支持两种模式：
  - LocalVectorStore: 本地字符串匹配（零依赖，用于 fallback）
  - APIEmbeddingStore: Embedding API + ChromaDB 语义检索（推荐）
"""

import uuid
from difflib import SequenceMatcher

import chromadb
from openai import OpenAI

from app.config import config
from app.core.exceptions import VectorStoreError
from app.core.logging import log


class LocalVectorStore:
    """本地字符串匹配，零依赖，无需网络"""

    def __init__(self):
        self.faqs = []

    def add_faqs(self, faqs: list[dict]):
        """追加 FAQ 到本地列表"""
        self.faqs.extend(faqs)

    def _similarity(self, a: str, b: str) -> float:
        return SequenceMatcher(None, a.lower(), b.lower()).ratio()

    def search(self, query: str, top_k: int = 3):
        if not self.faqs:
            return {"distances": [[]], "metadatas": [[]]}

        scored = []
        for f in self.faqs:
            score = self._similarity(query, f["question"])
            scored.append((score, f))

        scored.sort(key=lambda x: x[0], reverse=True)
        top = scored[:top_k]

        return {
            "distances": [[1 - s[0] for s in top]],
            "metadatas": [[{"question": s[1]["question"], "answer": s[1]["answer"]} for s in top]],
        }

    def clear(self):
        self.faqs = []

    def count(self) -> int:
        return len(self.faqs)


class APIEmbeddingStore:
    """
    Embedding API + ChromaDB 语义检索
    需配置 EMBEDDING_API_KEY / EMBEDDING_API_URL / EMBEDDING_API_MODEL
    支持 OpenAI、SiliconFlow、Azure OpenAI 等兼容接口
    """

    def __init__(self):
        if not config.EMBEDDING_API_KEY:
            raise VectorStoreError("EMBEDDING_MODE=api 时，必须配置 EMBEDDING_API_KEY")

        self.client = OpenAI(
            api_key=config.EMBEDDING_API_KEY,
            base_url=config.EMBEDDING_API_URL or None,
        )
        self.chroma_client = chromadb.PersistentClient(path=config.CHROMA_PERSIST_DIR)
        self.collection = self.chroma_client.get_or_create_collection(
            name="faq_collection",
            metadata={"hnsw:space": "cosine"},
        )

    def _get_embedding(self, text: str) -> list[float]:
        try:
            resp = self.client.embeddings.create(
                model=config.EMBEDDING_API_MODEL,
                input=text,
            )
            return resp.data[0].embedding
        except Exception as e:
            log.error(f"Embedding API 调用失败: {e}")
            raise VectorStoreError(f"Embedding API 调用失败: {e}")

    def add_faqs(self, faqs: list[dict]):
        if not faqs:
            return

        texts = [f["question"] for f in faqs]
        embeddings = [self._get_embedding(t) for t in texts]

        # 使用 UUID 生成唯一 ID，避免重复添加冲突
        ids = [f"faq_{uuid.uuid4().hex[:12]}" for _ in range(len(faqs))]

        self.collection.add(
            embeddings=embeddings,
            documents=texts,
            metadatas=[{"question": f["question"], "answer": f["answer"]} for f in faqs],
            ids=ids,
        )

    def search(self, query: str, top_k: int = 3):
        try:
            embedding = self._get_embedding(query)
            return self.collection.query(
                query_embeddings=[embedding],
                n_results=top_k,
                include=["metadatas", "distances", "documents"],
            )
        except Exception as e:
            log.error(f"向量检索失败: {e}")
            raise VectorStoreError(f"向量检索失败: {e}")

    def clear(self):
        try:
            self.chroma_client.delete_collection(name="faq_collection")
        except Exception:
            pass
        self.collection = self.chroma_client.get_or_create_collection(
            name="faq_collection",
            metadata={"hnsw:space": "cosine"},
        )

    def count(self) -> int:
        return self.collection.count()


def _create_store():
    """根据配置创建合适的存储后端"""
    if config.EMBEDDING_MODE == "api":
        try:
            store = APIEmbeddingStore()
            log.info(f"使用 Embedding API 模式 ({config.EMBEDDING_API_MODEL})")
            return store
        except Exception as e:
            log.warning(f"Embedding API 初始化失败: {e}")
            log.warning("自动降级为本地字符串匹配")
            return LocalVectorStore()
    return LocalVectorStore()


# 全局向量存储实例
vector_store = _create_store()
