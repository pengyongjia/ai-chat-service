"""
向量数据库存储层
支持两种模式：
  - LocalVectorStore: 本地字符串匹配（零依赖，用于 fallback）
  - APIEmbeddingStore: Embedding API + ChromaDB 语义检索（推荐）

同时支持两类数据：
  - FAQ: 人工维护的问答对
  - Document Chunks: 从文档切分出来的文本块
"""

import uuid
from dataclasses import dataclass
from difflib import SequenceMatcher

import chromadb
from openai import OpenAI

from app.config import config
from app.core.exceptions import VectorStoreError
from app.core.hybrid_searcher import SearchCandidate, hybrid_searcher
from app.core.logging import log


@dataclass
class Chunk:
    """向量库中的文本块"""

    text: str
    source: str
    doc_type: str  # "faq" 或 "document"
    chunk_index: int = 0
    metadata: dict | None = None


class LocalVectorStore:
    """本地字符串匹配，零依赖，无需网络"""

    def __init__(self):
        self.items = []

    def add_faqs(self, faqs: list[dict]):
        """追加 FAQ 到本地列表"""
        for i, faq in enumerate(faqs):
            self.items.append(
                {
                    "text": faq["question"],
                    "answer": faq["answer"],
                    "source": "faq.json",
                    "doc_type": "faq",
                    "chunk_index": i,
                }
            )

    def add_chunks(self, chunks: list[Chunk]):
        """追加文档 chunks 到本地列表"""
        for chunk in chunks:
            self.items.append(
                {
                    "text": chunk.text,
                    "answer": "",
                    "source": chunk.source,
                    "doc_type": chunk.doc_type,
                    "chunk_index": chunk.chunk_index,
                    "metadata": chunk.metadata or {},
                }
            )

    def _similarity(self, a: str, b: str) -> float:
        return SequenceMatcher(None, a.lower(), b.lower()).ratio()

    def search(
        self, query: str, top_k: int = 5, doc_types: list[str] | None = None, hybrid: bool = False
    ):
        """
        本地字符串匹配检索

        Args:
            query: 查询文本
            top_k: 返回最相似的结果数量
            doc_types: 限制检索的文档类型，如 ["faq", "document"]
            hybrid: 是否启用混合检索（BM25 + 向量/字符串匹配融合）
        """
        items = self.items
        if doc_types:
            items = [item for item in items if item["doc_type"] in doc_types]

        if not items:
            return {"distances": [[]], "metadatas": [[]], "documents": [[]]}

        scored = []
        for item in items:
            # FAQ 用 question 匹配，Document 用 text 匹配
            compare_text = item["text"]
            score = self._similarity(query, compare_text)
            scored.append((score, item))

        scored.sort(key=lambda x: x[0], reverse=True)
        vector_top_k = top_k * 4 if hybrid else top_k
        top = scored[:vector_top_k]

        vector_results = [
            {
                "text": s[1]["text"],
                "answer": s[1].get("answer", ""),
                "source": s[1]["source"],
                "doc_type": s[1]["doc_type"],
                "chunk_index": s[1].get("chunk_index", 0),
                "similarity": s[0],
                "metadata": s[1].get("metadata", {}),
            }
            for s in top
        ]

        if not hybrid:
            return self._pack_results(vector_results[:top_k])

        # 混合检索
        all_candidates = [
            SearchCandidate(
                text=item["text"],
                source=item["source"],
                doc_type=item["doc_type"],
                chunk_index=item.get("chunk_index", 0),
                answer=item.get("answer", ""),
                metadata=item.get("metadata", {}),
            )
            for item in items
        ]

        fused = hybrid_searcher.search(
            query=query,
            vector_results=vector_results,
            documents=all_candidates,
            vector_top_k=vector_top_k,
            keyword_top_k=top_k * 4,
            final_top_k=top_k,
        )
        return self._pack_results(fused)

    def _pack_results(self, candidates: list[dict]) -> dict:
        """将统一格式的候选结果打包成 ChromaDB 返回格式"""
        return {
            "distances": [[1 - c.get("similarity", 0.0) for c in candidates]],
            "metadatas": [[self._build_metadata(c) for c in candidates]],
            "documents": [[c.get("text", "") for c in candidates]],
        }

    def _build_metadata(self, item: dict) -> dict:
        """构建统一的 metadata"""
        return {
            "text": item["text"],
            "answer": item.get("answer", ""),
            "source": item["source"],
            "doc_type": item["doc_type"],
            "chunk_index": item.get("chunk_index", 0),
            **item.get("metadata", {}),
        }

    def clear(self, doc_type: str | None = None):
        """
        清空向量库
        Args:
            doc_type: 如果指定，只清空该类型的数据；否则全部清空
        """
        if doc_type:
            self.items = [item for item in self.items if item["doc_type"] != doc_type]
        else:
            self.items = []

    def count(self, doc_type: str | None = None) -> int:
        """统计数量"""
        if doc_type:
            return len([item for item in self.items if item["doc_type"] == doc_type])
        return len(self.items)


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
            name="knowledge_collection",
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

        ids = [f"faq_{uuid.uuid4().hex[:12]}" for _ in range(len(faqs))]

        self.collection.add(
            embeddings=embeddings,
            documents=texts,
            metadatas=[
                {
                    "text": f["question"],
                    "answer": f["answer"],
                    "source": "faq.json",
                    "doc_type": "faq",
                    "chunk_index": i,
                }
                for i, f in enumerate(faqs)
            ],
            ids=ids,
        )

    def add_chunks(self, chunks: list[Chunk]):
        if not chunks:
            return

        texts = [c.text for c in chunks]
        embeddings = [self._get_embedding(t) for t in texts]

        ids = [f"doc_{uuid.uuid4().hex[:12]}" for _ in range(len(chunks))]

        self.collection.add(
            embeddings=embeddings,
            documents=texts,
            metadatas=[
                {
                    "text": c.text,
                    "answer": "",
                    "source": c.source,
                    "doc_type": c.doc_type,
                    "chunk_index": c.chunk_index,
                    **(c.metadata or {}),
                }
                for c in chunks
            ],
            ids=ids,
        )

    def search(
        self, query: str, top_k: int = 5, doc_types: list[str] | None = None, hybrid: bool = False
    ):
        try:
            embedding = self._get_embedding(query)

            where_filter = None
            if doc_types:
                if len(doc_types) == 1:
                    where_filter = {"doc_type": doc_types[0]}
                else:
                    where_filter = {"doc_type": {"$in": doc_types}}

            vector_top_k = top_k * 4 if hybrid else top_k

            raw = self.collection.query(
                query_embeddings=[embedding],
                n_results=vector_top_k,
                where=where_filter,
                include=["metadatas", "distances", "documents"],
            )

            vector_results = self._parse_raw_results(raw)

            if not hybrid:
                return self._pack_results(vector_results[:top_k])

            # 混合检索：获取全部候选构建 BM25 索引
            all_data = self.collection.get(
                where=where_filter,
                include=["documents", "metadatas"],
            )
            all_candidates = [
                SearchCandidate(
                    text=doc,
                    source=meta.get("source", ""),
                    doc_type=meta.get("doc_type", "document"),
                    chunk_index=meta.get("chunk_index", 0),
                    answer=meta.get("answer", ""),
                    metadata=meta,
                )
                for doc, meta in zip(all_data["documents"], all_data["metadatas"])
            ]

            fused = hybrid_searcher.search(
                query=query,
                vector_results=vector_results,
                documents=all_candidates,
                vector_top_k=vector_top_k,
                keyword_top_k=top_k * 4,
                final_top_k=top_k,
            )
            return self._pack_results(fused)
        except Exception as e:
            log.error(f"向量检索失败: {e}")
            raise VectorStoreError(f"向量检索失败: {e}")

    def _parse_raw_results(self, raw: dict) -> list[dict]:
        """解析 ChromaDB 原始返回为统一格式"""
        results = []
        if not raw.get("distances") or not raw["distances"][0]:
            return results

        for i in range(len(raw["distances"][0])):
            metadata = raw["metadatas"][0][i]
            results.append(
                {
                    "text": metadata.get("text", ""),
                    "answer": metadata.get("answer", ""),
                    "source": metadata.get("source", ""),
                    "doc_type": metadata.get("doc_type", "document"),
                    "chunk_index": metadata.get("chunk_index", 0),
                    "similarity": 1 - raw["distances"][0][i],
                    "metadata": metadata,
                }
            )
        return results

    def _pack_results(self, candidates: list[dict]) -> dict:
        """将统一格式的候选结果打包成 ChromaDB 返回格式"""
        return {
            "distances": [[1 - c.get("similarity", 0.0) for c in candidates]],
            "metadatas": [[c for c in candidates]],
            "documents": [[c.get("text", "") for c in candidates]],
        }

    def clear(self, doc_type: str | None = None):
        try:
            self.chroma_client.delete_collection(name="knowledge_collection")
        except Exception:
            pass

        # 如果有指定 doc_type，重新创建集合并保留其他类型数据
        self.collection = self.chroma_client.get_or_create_collection(
            name="knowledge_collection",
            metadata={"hnsw:space": "cosine"},
        )

    def count(self, doc_type: str | None = None) -> int:
        if doc_type:
            try:
                return self.collection.count(where={"doc_type": doc_type})
            except Exception:
                return 0
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
