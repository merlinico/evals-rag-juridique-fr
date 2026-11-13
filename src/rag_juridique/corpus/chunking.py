"""Chunkers implementing the frozen Chunker protocol.

Owned by agent (c) retrieval. Temporal version resolution is applied when
``ArticleVersion`` rows are supplied; otherwise ``as_of`` is a documented no-op.
"""

from __future__ import annotations

from datetime import date

from rag_juridique.contracts.chunking import Chunk, Chunker
from rag_juridique.contracts.corpus import Article, ArticleVersion


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


def version_in_force(version: ArticleVersion, as_of: date) -> bool:
    """Return True if ``version`` is in force on ``as_of`` (debut inclusive, fin exclusive)."""
    if version.debut is not None and as_of < version.debut:
        return False
    if version.fin is not None and as_of >= version.fin:
        return False
    return True


def resolve_article_as_of(
    article: Article,
    versions: list[ArticleVersion],
    as_of: date,
) -> Article:
    """Return a copy of ``article`` with text/title from the version in force at ``as_of``.

    Matching versions are those with ``article_id == article.id`` (or tip
    ``version_id == article.id``). If none are in force, the original article
    is returned unchanged.
    """
    candidates = [
        v
        for v in versions
        if v.article_id == article.id or v.version_id == article.id
    ]
    in_force = [v for v in candidates if version_in_force(v, as_of)]
    if not in_force:
        return article
    # Prefer the version whose interval starts latest (most specific).
    chosen = max(in_force, key=lambda v: v.debut or date.min)
    return article.model_copy(
        update={
            "text": chosen.text,
            "title": chosen.titre or article.title,
            "num": chosen.num or article.num,
            "etat": chosen.etat,
        }
    )


def apply_versions(
    articles: list[Article],
    versions: list[ArticleVersion] | None,
    as_of: date | None,
) -> list[Article]:
    """Apply temporal versions when both ``versions`` and ``as_of`` are provided."""
    if as_of is None or not versions:
        return articles
    return [resolve_article_as_of(a, versions, as_of) for a in articles]


def hierarchy_parent_context(article: Article) -> str | None:
    """Build a livre/titre/chapitre (or contexte) preamble for structural chunking."""
    parts: list[str] = []
    if article.livre:
        parts.append(f"Livre : {article.livre}")
    if article.titre:
        parts.append(f"Titre : {article.titre}")
    if article.chapitre:
        parts.append(f"Chapitre : {article.chapitre}")
    if parts:
        return " > ".join(parts)
    # MVP snapshot stores hierarchy only in ``contexte``.
    ctx = (article.contexte or "").strip()
    return ctx or None


def _version_meta(
    article: Article,
    versions: list[ArticleVersion] | None,
    as_of: date | None,
) -> tuple[str | None, date | None]:
    if as_of is None or not versions:
        return None, None
    candidates = [
        v
        for v in versions
        if (v.article_id == article.id or v.version_id == article.id)
        and version_in_force(v, as_of)
    ]
    if not candidates:
        return None, as_of
    chosen = max(candidates, key=lambda v: v.debut or date.min)
    return chosen.version_id, as_of


def chunk_articles(
    articles: list[Article],
    chunk_size: int = 800,
    overlap: int = 100,
    *,
    versions: list[ArticleVersion] | None = None,
    as_of: date | None = None,
    parent_context: bool = False,
) -> list[Chunk]:
    """Découpe les articles en chunks de caractères (configurable)."""
    resolved = apply_versions(articles, versions, as_of)
    chunks: list[Chunk] = []
    for original, article in zip(articles, resolved, strict=True):
        header = f"{article.title}\n"
        body = article.text
        preamble = hierarchy_parent_context(article) if parent_context else None
        if preamble:
            full = f"{preamble}\n{header}{body}"
        else:
            full = header + body
        windows = _split_windows(full, chunk_size=chunk_size, overlap=overlap)
        version_id, chunk_as_of = _version_meta(original, versions, as_of)
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
                    parent_context=preamble,
                    version_id=version_id,
                    as_of=chunk_as_of,
                )
            )
    return chunks


class FixedSizeChunker:
    """MVP fixed-size chunker implementing the frozen Chunker protocol."""

    name = "fixed_size"

    def __init__(
        self,
        chunk_size: int = 800,
        overlap: int = 100,
        versions: list[ArticleVersion] | None = None,
    ) -> None:
        self.chunk_size = chunk_size
        self.overlap = overlap
        self.versions = versions

    def chunk(
        self,
        articles: list[Article],
        *,
        as_of: date | None = None,
    ) -> list[Chunk]:
        return chunk_articles(
            articles,
            chunk_size=self.chunk_size,
            overlap=self.overlap,
            versions=self.versions,
            as_of=as_of,
            parent_context=False,
        )


class PerArticleChunker:
    """One chunk per article (full text + title)."""

    name = "per_article"

    def __init__(self, versions: list[ArticleVersion] | None = None) -> None:
        self.versions = versions

    def chunk(
        self,
        articles: list[Article],
        *,
        as_of: date | None = None,
    ) -> list[Chunk]:
        resolved = apply_versions(articles, self.versions, as_of)
        chunks: list[Chunk] = []
        for original, article in zip(articles, resolved, strict=True):
            text = f"{article.title}\n{article.text}".strip()
            version_id, chunk_as_of = _version_meta(original, self.versions, as_of)
            chunks.append(
                Chunk(
                    chunk_id=f"{article.id}#0",
                    article_id=article.id,
                    article_num=article.num,
                    title=article.title,
                    text=text,
                    start_char=0,
                    end_char=len(text),
                    parent_context=None,
                    version_id=version_id,
                    as_of=chunk_as_of,
                )
            )
        return chunks


class StructuralChunker:
    """Fixed-size windows prefixed with hierarchy parent context.

    Uses ``livre`` / ``titre`` / ``chapitre`` when populated; falls back to
    MVP ``contexte`` strings. Parent context is stored on ``Chunk.parent_context``
    and prepended to indexed text.
    """

    name = "structural"

    def __init__(
        self,
        chunk_size: int = 800,
        overlap: int = 100,
        versions: list[ArticleVersion] | None = None,
    ) -> None:
        self.chunk_size = chunk_size
        self.overlap = overlap
        self.versions = versions

    def chunk(
        self,
        articles: list[Article],
        *,
        as_of: date | None = None,
    ) -> list[Chunk]:
        return chunk_articles(
            articles,
            chunk_size=self.chunk_size,
            overlap=self.overlap,
            versions=self.versions,
            as_of=as_of,
            parent_context=True,
        )


def get_chunker(
    name: str,
    *,
    chunk_size: int = 800,
    overlap: int = 100,
    versions: list[ArticleVersion] | None = None,
) -> Chunker:
    """Factory for the three phase-2 chunkers."""
    key = name.strip().lower()
    if key in {"fixed_size", "fixed", "fixed-size"}:
        return FixedSizeChunker(
            chunk_size=chunk_size, overlap=overlap, versions=versions
        )
    if key in {"per_article", "article", "per-article"}:
        return PerArticleChunker(versions=versions)
    if key in {"structural", "structure", "structural_parent"}:
        return StructuralChunker(
            chunk_size=chunk_size, overlap=overlap, versions=versions
        )
    raise ValueError(f"Unknown chunker: {name!r}")


def as_chunker(chunker: Chunker) -> Chunker:
    """Type-narrow helper for callers that accept any Chunker."""
    return chunker


__all__ = [
    "FixedSizeChunker",
    "PerArticleChunker",
    "StructuralChunker",
    "apply_versions",
    "as_chunker",
    "chunk_articles",
    "get_chunker",
    "hierarchy_parent_context",
    "resolve_article_as_of",
    "version_in_force",
]
