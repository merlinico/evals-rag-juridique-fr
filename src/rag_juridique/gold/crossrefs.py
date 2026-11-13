"""Cross-reference resolution for multi-hop gold questions.

Prefer a versioned corpus graph from agent (a) when present:
`data/corpus/cross_refs.json` (list of CrossRef-shaped objects).
Otherwise extract explicit article citations from article text so the
pipeline works on the MVP snapshot and extends automatically later.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

from rag_juridique.contracts.corpus import Article, CrossRef, CrossRefKind
from rag_juridique.gold.textutil import extract_article_nums, normalize_article_num

# Optional path written by corpus agent (a).
DEFAULT_CROSS_REFS_PATH = (
    Path(__file__).resolve().parents[3] / "data" / "corpus" / "cross_refs.json"
)

_RANGE_RE = re.compile(
    r"articles?\s+(L\.\s*\d+(?:-\d+)*)\s+à\s+(L\.\s*\d+(?:-\d+)*)",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class ResolvedEdge:
    source_id: str
    source_num: str
    target_id: str
    target_num: str
    kind: CrossRefKind
    origin: str  # "corpus_file" | "text_extract"


def _expand_range(start_num: str, end_num: str, by_num: dict[str, Article]) -> list[str]:
    """Best-effort expansion of 'L. 121-2 à L. 121-4' within the loaded corpus."""
    start = normalize_article_num(start_num)
    end = normalize_article_num(end_num)
    if start == end:
        return [start]
    # Same prefix family: L. 121-*
    def parts(n: str) -> tuple[str, list[int]] | None:
        m = re.match(r"L\.\s*(\d+(?:-\d+)*)", n)
        if not m:
            return None
        bits = [int(x) for x in m.group(1).split("-")]
        return m.group(1), bits

    sp = parts(start)
    ep = parts(end)
    if not sp or not ep:
        return [start, end]
    # Only expand simple last-component ranges with shared stem.
    if len(sp[1]) != len(ep[1]) or sp[1][:-1] != ep[1][:-1]:
        return [start, end]
    lo, hi = sp[1][-1], ep[1][-1]
    if lo > hi:
        lo, hi = hi, lo
    stem = "-".join(str(x) for x in sp[1][:-1])
    out: list[str] = []
    for i in range(lo, hi + 1):
        cand = normalize_article_num(f"L. {stem}-{i}" if stem else f"L. {i}")
        if cand in by_num:
            out.append(cand)
    return out or [start, end]


def extract_edges_from_text(
    articles: list[Article],
) -> list[ResolvedEdge]:
    by_num = {a.num: a for a in articles}
    # Also index folded variants
    by_num_norm = {normalize_article_num(a.num): a for a in articles}
    edges: list[ResolvedEdge] = []
    seen: set[tuple[str, str]] = set()

    for art in articles:
        text = art.text
        # Expand ranges first so members become targets when present.
        for m in _RANGE_RE.finditer(text):
            for target_num in _expand_range(m.group(1), m.group(2), by_num_norm):
                target = by_num_norm.get(normalize_article_num(target_num))
                if not target or target.id == art.id:
                    continue
                key = (art.id, target.id)
                if key in seen:
                    continue
                seen.add(key)
                edges.append(
                    ResolvedEdge(
                        source_id=art.id,
                        source_num=art.num,
                        target_id=target.id,
                        target_num=target.num,
                        kind=CrossRefKind.RENVOI,
                        origin="text_extract",
                    )
                )

        for num in extract_article_nums(text):
            target = by_num_norm.get(normalize_article_num(num))
            if not target or target.id == art.id:
                continue
            key = (art.id, target.id)
            if key in seen:
                continue
            seen.add(key)
            edges.append(
                ResolvedEdge(
                    source_id=art.id,
                    source_num=art.num,
                    target_id=target.id,
                    target_num=target.num,
                    kind=CrossRefKind.EXPLICIT_CITATION,
                    origin="text_extract",
                )
            )
    return edges


def load_cross_refs_file(path: Path | str) -> list[CrossRef]:
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    items = raw if isinstance(raw, list) else raw.get("cross_refs") or raw.get("items") or []
    return [CrossRef.model_validate(item) for item in items]


def resolve_cross_refs(
    articles: list[Article],
    cross_refs_path: Path | str | None = DEFAULT_CROSS_REFS_PATH,
) -> list[ResolvedEdge]:
    """Load agent-(a) graph if present, else extract from article text."""
    path = Path(cross_refs_path) if cross_refs_path else None
    by_id = {a.id: a for a in articles}
    if path is not None and path.is_file():
        edges: list[ResolvedEdge] = []
        for ref in load_cross_refs_file(path):
            src = by_id.get(ref.source_article_id)
            tgt = by_id.get(ref.target_article_id)
            if not src or not tgt:
                continue
            edges.append(
                ResolvedEdge(
                    source_id=src.id,
                    source_num=src.num,
                    target_id=tgt.id,
                    target_num=tgt.num,
                    kind=ref.kind,
                    origin="corpus_file",
                )
            )
        if edges:
            return edges
    return extract_edges_from_text(articles)
