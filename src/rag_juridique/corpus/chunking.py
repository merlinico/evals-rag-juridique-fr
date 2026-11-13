from __future__ import annotations

from dataclasses import dataclass

from rag_juridique.corpus.loader import Article


@dataclass(frozen=True)
class Chunk:
    chunk_id: str
    article_id: str
    article_num: str
    title: str
    text: str
    start_char: int
    end_char: int


def _split_windows(text: str, chunk_size: int, overlap: int) -> list[tuple[int, int, str]]:
    if chunk_size <= 0:
        raise ValueError("chunk_size must be > 0")
    if overlap < 0 or overlap >= chunk_size:
        raise ValueError("overlap must be >= 0 and < chunk_size")
    if len(text) <= chunk_size:
        return [(0, len(text), text)]

    windows: list[tuple[int, int, str]] = []
    start = 0
    step = chunk_size - overlap
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
