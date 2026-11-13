"""Chunk and Chunker protocol."""

from __future__ import annotations

from datetime import date
from typing import Protocol, runtime_checkable

from pydantic import BaseModel, ConfigDict, Field

from rag_juridique.contracts.corpus import Article


class Chunk(BaseModel):
    """Indexed retrieval unit derived from one or more articles."""

    model_config = ConfigDict(extra="ignore")

    chunk_id: str
    article_id: str
    article_num: str
    title: str
    text: str
    start_char: int = 0
    end_char: int = 0
    parent_context: str | None = Field(
        default=None,
        description="Structural chunker: livre/titre/chapitre preamble",
    )
    version_id: str | None = Field(
        default=None, description="ArticleVersion.version_id when temporal"
    )
    as_of: date | None = None


@runtime_checkable
class Chunker(Protocol):
    """Produces chunks from articles.

    Implementations: fixed-size, per-article, structural-with-parent-context.
    """

    name: str

    def chunk(
        self,
        articles: list[Article],
        *,
        as_of: date | None = None,
    ) -> list[Chunk]:
        """Chunk articles; optional as_of selects versions in force."""
        ...
