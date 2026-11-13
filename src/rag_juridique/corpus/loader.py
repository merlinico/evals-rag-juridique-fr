from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class Article:
    id: str
    num: str
    title: str
    text: str
    contexte: str = ""
    etat: str = "VIGUEUR"

    @property
    def display_id(self) -> str:
        """Identifiant cité dans les réponses (numéro d'article)."""
        return self.num


@dataclass(frozen=True)
class Corpus:
    articles: list[Article]
    source: dict[str, Any]
    snapshot_id: str

    def by_id(self) -> dict[str, Article]:
        return {a.id: a for a in self.articles}

    def by_num(self) -> dict[str, Article]:
        return {a.num: a for a in self.articles}

    def __len__(self) -> int:
        return len(self.articles)


def default_corpus_path() -> Path:
    return Path(__file__).resolve().parents[3] / "data" / "corpus" / "articles.json"


def load_corpus(path: Path | str | None = None) -> Corpus:
    corpus_path = Path(path) if path else default_corpus_path()
    raw = json.loads(corpus_path.read_text(encoding="utf-8"))
    source = dict(raw.get("source") or {})
    articles = [
        Article(
            id=item["id"],
            num=item["num"],
            title=item.get("title") or f"Article {item['num']}",
            text=item["text"],
            contexte=item.get("contexte") or "",
            etat=item.get("etat") or "VIGUEUR",
        )
        for item in raw["articles"]
    ]
    return Corpus(
        articles=articles,
        source=source,
        snapshot_id=str(source.get("snapshot_id") or "unknown"),
    )
