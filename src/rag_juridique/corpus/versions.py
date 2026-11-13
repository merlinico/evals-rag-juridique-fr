"""ArticleVersion helpers: index and resolve the version in force at a date."""

from __future__ import annotations

from collections import defaultdict
from datetime import date

from rag_juridique.contracts.corpus import ArticleVersion

# LEGI sentinel for "still in force"
_OPEN_END = date(2999, 1, 1)


def parse_legi_date(value: str | date | None) -> date | None:
    if value is None or value == "":
        return None
    if isinstance(value, date):
        return value
    text = str(value).strip()[:10]
    if not text or text.startswith("0001"):
        return None
    try:
        d = date.fromisoformat(text)
    except ValueError:
        return None
    if d >= _OPEN_END:
        return None
    return d


def version_in_force(
    versions: list[ArticleVersion],
    as_of: date,
) -> ArticleVersion | None:
    """Return the version whose ``[debut, fin)`` interval covers ``as_of``.

    ``fin is None`` means still in force (open interval).
    When several match, prefer the latest ``debut``.
    """
    matches: list[ArticleVersion] = []
    for ver in versions:
        debut = ver.debut
        fin = ver.fin
        if debut is not None and as_of < debut:
            continue
        if fin is not None and as_of >= fin:
            continue
        # If debut is unknown, still accept when fin allows (rare)
        matches.append(ver)
    if not matches:
        return None
    matches.sort(key=lambda v: v.debut or date.min, reverse=True)
    return matches[0]


def index_versions_by_article(
    versions: list[ArticleVersion],
) -> dict[str, list[ArticleVersion]]:
    by_article: dict[str, list[ArticleVersion]] = defaultdict(list)
    for ver in versions:
        by_article[ver.article_id].append(ver)
    for lst in by_article.values():
        lst.sort(key=lambda v: v.debut or date.min)
    return dict(by_article)
