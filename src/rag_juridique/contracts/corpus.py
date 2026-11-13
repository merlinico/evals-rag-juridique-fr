"""Corpus contracts: articles, LEGI versions, cross-references."""

from __future__ import annotations

from datetime import date
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class CrossRefKind(str, Enum):
    """How one article points at another."""

    EXPLICIT_CITATION = "explicit_citation"
    RENVOI = "renvoi"
    OTHER = "other"


class Article(BaseModel):
    """Canonical article unit shared by corpus, chunking, and retrieval.

    Hierarchy fields (livre / titre / chapitre) are optional so the MVP
    snapshot remains valid; phase-2 corpus fills them from LEGI structure.
    """

    model_config = ConfigDict(extra="ignore")

    id: str = Field(..., description="Stable LEGIARTI id")
    num: str = Field(..., description="Human article number, e.g. 'L. 111-1'")
    title: str
    text: str
    texte_cid: str | None = Field(
        default=None, description="Parent code / texte LEGITEXT id"
    )
    etat: str = "VIGUEUR"
    contexte: str = ""
    code: str | None = Field(
        default=None, description="Short code key: civil | consommation | travail"
    )
    livre: str | None = None
    titre: str | None = None
    chapitre: str | None = None

    @property
    def display_id(self) -> str:
        """Identifiant cité dans les réponses (numéro d'article)."""
        return self.num


class ArticleVersion(BaseModel):
    """A dated LEGI version of an article (version in force over an interval)."""

    model_config = ConfigDict(extra="ignore")

    version_id: str = Field(..., description="LEGIARTI id of this version")
    article_id: str = Field(
        ...,
        description="Logical article key (often the current / tip version id)",
    )
    num: str
    text: str
    etat: str = "VIGUEUR"
    debut: date | None = Field(
        default=None, description="Inclusive start of force (YYYY-MM-DD)"
    )
    fin: date | None = Field(
        default=None, description="Exclusive end of force; null = still in force"
    )
    titre: str | None = None


class CrossRef(BaseModel):
    """Directed reference from one article to another."""

    model_config = ConfigDict(extra="ignore")

    source_article_id: str
    target_article_id: str
    kind: CrossRefKind = CrossRefKind.EXPLICIT_CITATION
    target_num: str | None = Field(
        default=None, description="Surface form of the cited article number"
    )
    span_start: int | None = Field(default=None, description="Char offset in source text")
    span_end: int | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
