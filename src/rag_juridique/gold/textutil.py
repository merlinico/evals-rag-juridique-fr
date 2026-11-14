"""Text helpers for gold generation and filtering."""

from __future__ import annotations

import re
import unicodedata

_TOKEN_RE = re.compile(r"[\w\-']+", re.UNICODE)
_ARTICLE_NUM_RE = re.compile(
    r"L\.\s*\d+(?:-\d+)*(?:-\d+)?",
    re.IGNORECASE,
)
_WS_RE = re.compile(r"\s+")


def normalize_ws(text: str) -> str:
    return _WS_RE.sub(" ", text).strip()


def fold(text: str) -> str:
    """Lowercase + strip accents for fuzzy comparisons."""
    nfkd = unicodedata.normalize("NFKD", text)
    return "".join(c for c in nfkd if not unicodedata.combining(c)).lower()


def tokens(text: str, *, min_len: int = 3) -> set[str]:
    return {t for t in _TOKEN_RE.findall(fold(text)) if len(t) >= min_len}


def jaccard(a: set[str], b: set[str]) -> float:
    if not a and not b:
        return 1.0
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def normalize_article_num(num: str) -> str:
    """Canonical surface form: 'L. 217-3'."""
    m = _ARTICLE_NUM_RE.search(num.replace(" ", ""))
    raw = m.group(0) if m else num
    raw = re.sub(r"(?i)^l\.\s*", "L. ", raw)
    raw = re.sub(r"\s+", "", raw)
    # L.217-3 -> L. 217-3
    raw = re.sub(r"(?i)^L\.?", "L. ", raw)
    return normalize_ws(raw)


def extract_article_nums(text: str) -> list[str]:
    found: list[str] = []
    seen: set[str] = set()
    for m in _ARTICLE_NUM_RE.finditer(text):
        num = normalize_article_num(m.group(0))
        key = fold(num)
        if key not in seen:
            seen.add(key)
            found.append(num)
    return found


def first_sentence(text: str, max_chars: int = 280) -> str:
    text = normalize_ws(text)
    for sep in (". ", " ; ", "; "):
        if sep in text:
            cut = text.split(sep, 1)[0].strip()
            if cut and not cut.endswith("."):
                cut += "."
            return cut[:max_chars]
    return text[:max_chars]


def snippet(text: str, max_chars: int = 220) -> str:
    text = normalize_ws(text)
    if len(text) <= max_chars:
        return text
    cut = text[:max_chars].rsplit(" ", 1)[0]
    return cut + "…"
