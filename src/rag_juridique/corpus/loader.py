"""Load the frozen LEGI corpus snapshot (articles, versions, cross-refs)."""

from __future__ import annotations

import gzip
import json
from collections.abc import Iterable
from datetime import date
from pathlib import Path
from typing import Any

from rag_juridique.contracts.corpus import Article, ArticleVersion, CrossRef
from rag_juridique.corpus.versions import index_versions_by_article, version_in_force


def corpus_dir() -> Path:
    return Path(__file__).resolve().parents[3] / "data" / "corpus"


def default_corpus_path() -> Path:
    """Prefer compressed snapshot when present; fall back to legacy JSON."""
    root = corpus_dir()
    for name in ("articles.json.gz", "articles.json"):
        path = root / name
        if path.is_file():
            return path
    return root / "articles.json.gz"


def default_versions_path() -> Path:
    root = corpus_dir()
    for name in ("versions.json.gz", "versions.json"):
        path = root / name
        if path.is_file():
            return path
    return root / "versions.json.gz"


def default_crossrefs_path() -> Path:
    root = corpus_dir()
    for name in ("crossrefs.json.gz", "crossrefs.json"):
        path = root / name
        if path.is_file():
            return path
    return root / "crossrefs.json.gz"


def _read_json(path: Path) -> Any:
    if path.suffix == ".gz" or path.name.endswith(".json.gz"):
        with gzip.open(path, "rt", encoding="utf-8") as fh:
            return json.load(fh)
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    data = json.dumps(payload, ensure_ascii=False, indent=2)
    if str(path).endswith(".gz"):
        with gzip.open(path, "wt", encoding="utf-8") as fh:
            fh.write(data)
            fh.write("\n")
    else:
        path.write_text(data + "\n", encoding="utf-8")


class Corpus:
    """In-memory article collection loaded from the frozen snapshot."""

    def __init__(
        self,
        articles: list[Article],
        source: dict[str, Any],
        snapshot_id: str,
        versions: list[ArticleVersion] | None = None,
        crossrefs: list[CrossRef] | None = None,
    ) -> None:
        self.articles = articles
        self.source = source
        self.snapshot_id = snapshot_id
        self.versions = list(versions or [])
        self.crossrefs = list(crossrefs or [])
        self._by_id = {a.id: a for a in articles}
        self._versions_by_article = index_versions_by_article(self.versions)
        self._crossrefs_from: dict[str, list[CrossRef]] = {}
        self._crossrefs_to: dict[str, list[CrossRef]] = {}
        for ref in self.crossrefs:
            self._crossrefs_from.setdefault(ref.source_article_id, []).append(ref)
            self._crossrefs_to.setdefault(ref.target_article_id, []).append(ref)

    def by_id(self) -> dict[str, Article]:
        return dict(self._by_id)

    def by_num(self, code: str | None = None) -> dict[str, Article]:
        out: dict[str, Article] = {}
        for a in self.articles:
            if code is not None and a.code != code:
                continue
            out[a.num] = a
        return out

    def articles_for_code(self, code: str) -> list[Article]:
        return [a for a in self.articles if a.code == code]

    def versions_for(self, article_id: str) -> list[ArticleVersion]:
        return list(self._versions_by_article.get(article_id, []))

    def version_at(self, article_id: str, as_of: date) -> ArticleVersion | None:
        """Return the ``ArticleVersion`` in force for ``article_id`` at ``as_of``."""
        return version_in_force(self.versions_for(article_id), as_of)

    def crossrefs_from(self, article_id: str) -> list[CrossRef]:
        return list(self._crossrefs_from.get(article_id, []))

    def crossrefs_to(self, article_id: str) -> list[CrossRef]:
        return list(self._crossrefs_to.get(article_id, []))

    def stats(self) -> dict[str, Any]:
        by_code: dict[str, int] = {}
        for a in self.articles:
            key = a.code or "unknown"
            by_code[key] = by_code.get(key, 0) + 1
        versions_by_code: dict[str, int] = {}
        for ver in self.versions:
            art = self._by_id.get(ver.article_id)
            key = (art.code if art else None) or "unknown"
            versions_by_code[key] = versions_by_code.get(key, 0) + 1
        refs_by_code: dict[str, int] = {}
        for ref in self.crossrefs:
            art = self._by_id.get(ref.source_article_id)
            key = (art.code if art else None) or "unknown"
            refs_by_code[key] = refs_by_code.get(key, 0) + 1
        return {
            "snapshot_id": self.snapshot_id,
            "n_articles": len(self.articles),
            "n_versions": len(self.versions),
            "n_crossrefs": len(self.crossrefs),
            "articles_by_code": by_code,
            "versions_by_code": versions_by_code,
            "crossrefs_by_code": refs_by_code,
        }

    def __len__(self) -> int:
        return len(self.articles)


def load_versions(path: Path | str | None = None) -> list[ArticleVersion]:
    versions_path = Path(path) if path else default_versions_path()
    if not versions_path.is_file():
        return []
    raw = _read_json(versions_path)
    items = raw["versions"] if isinstance(raw, dict) and "versions" in raw else raw
    return [ArticleVersion.model_validate(item) for item in items]


def load_crossrefs(path: Path | str | None = None) -> list[CrossRef]:
    refs_path = Path(path) if path else default_crossrefs_path()
    if not refs_path.is_file():
        return []
    raw = _read_json(refs_path)
    items = raw["crossrefs"] if isinstance(raw, dict) and "crossrefs" in raw else raw
    return [CrossRef.model_validate(item) for item in items]


def load_corpus(
    path: Path | str | None = None,
    *,
    versions_path: Path | str | None = None,
    crossrefs_path: Path | str | None = None,
    load_graph: bool = True,
) -> Corpus:
    """Load articles (+ optional versions / cross-refs) from the frozen snapshot.

    Parameters
    ----------
    path:
        Articles JSON (``.json`` or ``.json.gz``). Defaults to ``data/corpus/``.
    versions_path / crossrefs_path:
        Optional overrides; when ``load_graph`` is true, siblings next to the
        articles file are loaded automatically when present.
    """
    corpus_path = Path(path) if path else default_corpus_path()
    raw = _read_json(corpus_path)
    source = dict(raw.get("source") or {})
    articles = [Article.model_validate(item) for item in raw["articles"]]

    versions: list[ArticleVersion] = []
    crossrefs: list[CrossRef] = []
    if load_graph:
        vpath = Path(versions_path) if versions_path else None
        cpath = Path(crossrefs_path) if crossrefs_path else None
        if vpath is None:
            sibling = corpus_path.parent / (
                "versions.json.gz"
                if corpus_path.name.endswith(".gz")
                else "versions.json"
            )
            alt = corpus_path.parent / (
                "versions.json" if sibling.name.endswith(".gz") else "versions.json.gz"
            )
            vpath = sibling if sibling.is_file() else alt
        if cpath is None:
            sibling = corpus_path.parent / (
                "crossrefs.json.gz"
                if corpus_path.name.endswith(".gz")
                else "crossrefs.json"
            )
            alt = corpus_path.parent / (
                "crossrefs.json"
                if sibling.name.endswith(".gz")
                else "crossrefs.json.gz"
            )
            cpath = sibling if sibling.is_file() else alt
        versions = load_versions(vpath)
        crossrefs = load_crossrefs(cpath)

    return Corpus(
        articles=articles,
        source=source,
        snapshot_id=str(source.get("snapshot_id") or "unknown"),
        versions=versions,
        crossrefs=crossrefs,
    )


def write_corpus_snapshot(
    *,
    articles: Iterable[Article],
    source: dict[str, Any],
    versions: Iterable[ArticleVersion] | None = None,
    crossrefs: Iterable[CrossRef] | None = None,
    articles_path: Path | None = None,
    versions_path: Path | None = None,
    crossrefs_path: Path | None = None,
) -> dict[str, Path]:
    """Write compressed (or plain) snapshot files; used by the build script."""
    root = corpus_dir()
    articles_path = articles_path or (root / "articles.json.gz")
    versions_path = versions_path or (root / "versions.json.gz")
    crossrefs_path = crossrefs_path or (root / "crossrefs.json.gz")

    art_list = [a.model_dump(mode="json") for a in articles]
    source = dict(source)
    source["n_articles"] = len(art_list)
    _write_json(articles_path, {"source": source, "articles": art_list})

    ver_list = [v.model_dump(mode="json") for v in (versions or [])]
    _write_json(
        versions_path,
        {
            "source": {
                "snapshot_id": source.get("snapshot_id"),
                "n_versions": len(ver_list),
            },
            "versions": ver_list,
        },
    )

    ref_list = [r.model_dump(mode="json") for r in (crossrefs or [])]
    _write_json(
        crossrefs_path,
        {
            "source": {
                "snapshot_id": source.get("snapshot_id"),
                "n_crossrefs": len(ref_list),
            },
            "crossrefs": ref_list,
        },
    )
    return {
        "articles": articles_path,
        "versions": versions_path,
        "crossrefs": crossrefs_path,
    }
