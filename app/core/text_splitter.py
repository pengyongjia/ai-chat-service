"""
文本切分器
将长文档切分为适合 Embedding 和 LLM 上下文的小块
"""

import re
from dataclasses import dataclass


@dataclass
class TextChunk:
    """文本块"""

    text: str
    source: str
    chunk_index: int
    total_chunks: int = 0
    metadata: dict | None = None


class TextSplitter:
    """
    文本切分器
    支持多种切分策略：按长度、按段落、按 Markdown 标题
    """

    def __init__(
        self,
        chunk_size: int = 500,
        chunk_overlap: int = 50,
        separators: list[str] | None = None,
    ):
        """
        Args:
            chunk_size: 每个 chunk 的目标字符长度
            chunk_overlap: 相邻 chunk 之间的重叠字符数
            separators: 优先使用的分隔符列表（按优先级）
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.separators = separators or ["\n## ", "\n### ", "\n\n", "\n", "。", " "]

    def split(self, text: str, source: str = "") -> list[TextChunk]:
        """
        智能切分文本
        优先按语义分隔符切分，如果某个段落过长再按长度切分
        """
        if not text or not text.strip():
            return []

        # 第一步：按语义分隔符切分
        segments = self._split_by_separators(text)

        # 第二步：合并小段并控制长度
        chunks = self._merge_segments(segments)

        # 第三步：包装成 TextChunk
        total = len(chunks)
        return [
            TextChunk(
                text=chunk,
                source=source,
                chunk_index=i,
                total_chunks=total,
                metadata={"strategy": "semantic"},
            )
            for i, chunk in enumerate(chunks)
        ]

    def split_by_markdown_headers(self, text: str, source: str = "") -> list[TextChunk]:
        """
        按 Markdown 标题切分
        适合技术文档、帮助文档等结构化内容
        """
        if not text or not text.strip():
            return []

        # 匹配 ## / ### 开头的标题
        pattern = r"(?=\n##\s+[^\n]+\n|\n###\s+[^\n]+\n)"
        sections = re.split(pattern, text)

        chunks = []
        for i, section in enumerate(sections):
            section = section.strip()
            if not section:
                continue

            # 如果单个章节过长，再按长度切分
            if len(section) > self.chunk_size * 1.5:
                sub_chunks = self._split_by_length(section)
                for j, sub in enumerate(sub_chunks):
                    chunks.append(
                        TextChunk(
                            text=sub,
                            source=source,
                            chunk_index=len(chunks),
                            metadata={"strategy": "markdown_header", "section": i, "sub": j},
                        )
                    )
            else:
                chunks.append(
                    TextChunk(
                        text=section,
                        source=source,
                        chunk_index=len(chunks),
                        metadata={"strategy": "markdown_header", "section": i},
                    )
                )

        total = len(chunks)
        for chunk in chunks:
            chunk.total_chunks = total

        return chunks

    def _split_by_separators(self, text: str) -> list[str]:
        """按语义分隔符切分文本"""
        segments = [text]

        for separator in self.separators:
            new_segments = []
            for segment in segments:
                if len(segment) <= self.chunk_size:
                    new_segments.append(segment)
                else:
                    # 使用分隔符切分，但保留分隔符
                    parts = segment.split(separator)
                    for j, part in enumerate(parts):
                        if j < len(parts) - 1:
                            part = part + separator
                        if part.strip():
                            new_segments.append(part)
            segments = new_segments

        return [s.strip() for s in segments if s.strip()]

    def _merge_segments(self, segments: list[str]) -> list[str]:
        """
        合并小段并控制长度
        目标：每个 chunk 接近 chunk_size，但不超过 chunk_size * 1.3
        """
        if not segments:
            return []

        chunks = []
        current = ""

        for segment in segments:
            # 如果当前段本身就超长，先切分
            if len(segment) > self.chunk_size:
                if current:
                    chunks.append(current.strip())
                    current = ""

                sub_chunks = self._split_by_length(segment)
                chunks.extend(sub_chunks)
                continue

            # 如果加入当前段会超长，先保存当前 chunk
            if current and len(current) + len(segment) > self.chunk_size:
                chunks.append(current.strip())
                # 保留重叠部分
                current = self._get_overlap_text(current)

            current = current + segment if current else segment

        if current:
            chunks.append(current.strip())

        return [c for c in chunks if c]

    def _split_by_length(self, text: str) -> list[str]:
        """按固定长度切分文本，保留重叠"""
        if len(text) <= self.chunk_size:
            return [text.strip()] if text.strip() else []

        chunks = []
        start = 0

        while start < len(text):
            end = start + self.chunk_size
            chunk = text[start:end].strip()
            if chunk:
                chunks.append(chunk)
            start = end - self.chunk_overlap

        return chunks

    def _get_overlap_text(self, text: str) -> str:
        """获取文本末尾的重叠部分"""
        if len(text) <= self.chunk_overlap:
            return ""
        return text[-self.chunk_overlap :]


# 全局文本切分器实例
text_splitter = TextSplitter()
