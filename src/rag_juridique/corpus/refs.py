"""Parse explicit article citations / renvois from French legal text."""

from __future__ import annotations

import re
from collections.abc import Iterable, Mapping

from rag_juridique.contracts.corpus import CrossRef, CrossRefKind
from rag_juridique.corpus.hierarchy import normalize_article_num

# Matches: article L. 217-3 / articles L. 112-1 à L. 112-4-1 / art. R. 123-1
# Also bare Code civil nums: article 1240
_REF_PATTERN = re.compile(
    r"(?P<kind>articles?|arts?\.?)\s+"
    r"(?:"
    r"(?P<letter>[LRDA])\.?\s*(?P<body>[0-9]+(?:-[0-9]+)*(?:\s*(?:bis|ter|quater))?)"
    r"|"
    r"(?P<bare>[0-9]+(?:-[0-9]+)*(?:\s*(?:bis|ter|quater))?)"
    r")"
    r"(?:"
    r"\s*(?:,|et|à|au|aux|/|-)\s*"
    r"(?:"
    r"(?:articles?|arts?\.?)?\s*"
    r"(?P<letter2>[LRDA])\.?\s*"
    r"(?P<body2>[0-9]+(?:-[0-9]+)*(?:\s*(?:bis|ter|quater))?)"
    r"|"
    r"(?P<bare2>[0-9]+(?:-[0-9]+)*(?:\s*(?:bis|ter|quater))?)"
    r")"
    r")?",
    flags=re.IGNORECASE,
)

_RENVOI_HINT = re.compile(
    r"\b(renvoi|renvoyé|dans les conditions prévues|sous réserve de|"
    r"mentionné[es]?\s+à|prévu[es]?\s+à|visé[es]?\s+à)\b",
    flags=re.IGNORECASE,
)


def _surface(letter: str | None, body: str | None, bare: str | None) -> str | None:
    if letter and body:
        return normalize_article_num(f"{letter}. {body}")
    if bare:
        return normalize_article_num(bare)
    return None


def extract_reference_spans(text: str) -> list[tuple[str, int, int, CrossRefKind]]:
    """Return (normalized_num, span_start, span_end, kind) for citations in text."""
    if not text:
        return []
    out: list[tuple[str, int, int, CrossRefKind]] = []
    seen: set[tuple[str, int, int]] = set()
    for m in _REF_PATTERN.finditer(text):
        first = _surface(m.group("letter"), m.group("body"), m.group("bare"))
        second = _surface(m.group("letter2"), m.group("body2"), m.group("bare2"))
        window = text[max(0, m.start() - 40) : m.start()]
        kind = (
            CrossRefKind.RENVOI
            if _RENVOI_HINT.search(window)
            else CrossRefKind.EXPLICIT_CITATION
        )
        for num in (first, second):
            if not num:
                continue
            key = (num, m.start(), m.end())
            if key in seen:
                continue
            seen.add(key)
            out.append((num, m.start(), m.end(), kind))
    return out


def build_crossrefs(
    articles: Iterable,
    *,
    num_index: Mapping[tuple[str | None, str], str] | None = None,
) -> list[CrossRef]:
    """Build directed CrossRef edges resolved against an article index.

    ``num_index`` maps ``(code, normalized_num)`` → article id. When absent,
    it is built from ``articles``.
    """
    arts = list(articles)
    if num_index is None:
        index: dict[tuple[str | None, str], str] = {}
        for a in arts:
            key = (getattr(a, "code", None), normalize_article_num(a.num))
            index.setdefault(key, a.id)
            # also index without code for fallback
            index.setdefault((None, normalize_article_num(a.num)), a.id)
        num_index = index

    id_to_code = {a.id: getattr(a, "code", None) for a in arts}
    refs: list[CrossRef] = []
    seen_edges: set[tuple[str, str, str]] = set()

    for art in arts:
        code = id_to_code.get(art.id)
        for target_num, start, end, kind in extract_reference_spans(art.text):
            target_id = num_index.get((code, target_num)) or num_index.get(
                (None, target_num)
            )
            if not target_id or target_id == art.id:
                continue
            edge = (art.id, target_id, target_num)
            if edge in seen_edges:
                continue
            seen_edges.add(edge)
            refs.append(
                CrossRef(
                    source_article_id=art.id,
                    target_article_id=target_id,
                    kind=kind,
                    target_num=target_num,
                    span_start=start,
                    span_end=end,
                )
            )
    return refs
