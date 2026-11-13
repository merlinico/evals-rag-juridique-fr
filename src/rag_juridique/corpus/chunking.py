from __future__ import annotations

from datetime import date

from rag_juridique.contracts.chunking import Chunk, Chunker
from rag_juridique.contracts.corpus import Article


def _split_windows(text: str, chunk_size: int, overlap: int) -> list[tuple[int, int, str]]:
    if chunk_size <= 0:
        raise ValueError("chunk_size must be > 0")
    if overlap < 0 or overlap >= chunk_size:
        raise ValueError("overlap must be >= 0 and < chunk_size")
    if len(text) <= chunk_size:
        return [(0, len(text), text)]

    windows: list[tuple[int, int, str]] = []
    start = 0
    while start < len(text):
        end = min(start + chunk_size, len(text))
        # Prefer cutting on whitespace when not at the end.
        if end < len(text):
            cut = text.rfind(" ", start, end)
            if cut > start + chunk_size // 2:
                end = cut
        piece = text[start:end].strip()
        if piece:
            windows.append((start, end, piece))
        if end >= len(text):
            break
        start = max(end - overlap, start + 1)
    return windows


def chunk_articles(
    articles: list[Article],
    chunk_size: int = 800,
    overlap: int = 100,
) -> list[Chunk]:
    """Découpe les articles en chunks de caractères (configurable)."""
    chunks: list[Chunk] = []
    for article in articles:
        header = f"{article.title}\n"
        body = article.text
        full = header + body
        windows = _split_windows(full, chunk_size=chunk_size, overlap=overlap)
        for i, (start, end, text) in enumerate(windows):
            chunks.append(
                Chunk(
                    chunk_id=f"{article.id}#{i}",
                    article_id=article.id,
                    article_num=article.num,
                    title=article.title,
                    text=text,
                    start_char=start,
                    end_char=end,
                )
            )
    return chunks


class FixedSizeChunker:
    """MVP fixed-size chunker implementing the frozen Chunker protocol."""

    name = "fixed_size"

    def __init__(self, chunk_size: int = 800, overlap: int = 100) -> None:
        self.chunk_size = chunk_size
        self.overlap = overlap

    def chunk(
        self,
        articles: list[Article],
        *,
        as_of: date | None = None,
    ) -> list[Chunk]:
        del as_of  # temporal versions arrive in phase-2 corpus
        return chunk_articles(
            articles, chunk_size=self.chunk_size, overlap=self.overlap
        )


def as_chunker(chunker: Chunker) -> Chunker:
    """Type-narrow helper for callers that accept any Chunker."""
    return chunker
