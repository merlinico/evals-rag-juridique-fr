from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from rag_juridique.contracts.corpus import Article


class Corpus:
    """In-memory article collection loaded from the frozen snapshot."""

    def __init__(
        self,
        articles: list[Article],
        source: dict[str, Any],
        snapshot_id: str,
    ) -> None:
        self.articles = articles
        self.source = source
        self.snapshot_id = snapshot_id

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
    articles = [Article.model_validate(item) for item in raw["articles"]]
    return Corpus(
        articles=articles,
        source=source,
        snapshot_id=str(source.get("snapshot_id") or "unknown"),
    )
