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

# Protect legal / French abbreviations so ". " is not treated as EOS.
_PROTECT_PATTERNS = [
    # L. 217-3 / R. 123-1 / D. 111-4 / A. 1
    re.compile(r"\b([LRDA])\.\s*(\d[\d\-]*(?:\s*(?:bis|ter|quater))?)", re.I),
    # art. / Arts.
    re.compile(r"\b(arts?)\.", re.I),
    # n° / N°
    re.compile(r"\b(n°)", re.I),
    # 1° 2° etc.
    re.compile(r"(\d+°)"),
    # al. / als. / cf. / etc. / ss.
    re.compile(r"\b(als?|cf|etc|ss)\.", re.I),
    # M. Mme Dr (rare in codes but harmless)
    re.compile(r"\b(M|Mme|Dr|Pr)\.", re.I),
]

_SENT_END = re.compile(r"(?<=[.!?])\s+(?=[A-ZÀÂÄÇÉÈÊËÎÏÔÖÙÛÜŸ«\"'(\d])")


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


def _protect_abbrevs(text: str) -> tuple[str, list[str]]:
    store: list[str] = []

    def _sub(m: re.Match[str]) -> str:
        store.append(m.group(0))
        return f"⟦{len(store) - 1}⟧"

    out = text
    for pat in _PROTECT_PATTERNS:
        out = pat.sub(_sub, out)
    return out, store


def _restore_abbrevs(text: str, store: list[str]) -> str:
    def _sub(m: re.Match[str]) -> str:
        idx = int(m.group(1))
        return store[idx] if 0 <= idx < len(store) else m.group(0)

    return re.sub(r"⟦(\d+)⟧", _sub, text)


def split_sentences(text: str) -> list[str]:
    """Split on sentence boundaries without cutting legal abbreviations."""
    text = normalize_ws(text)
    if not text:
        return []
    protected, store = _protect_abbrevs(text)
    parts = _SENT_END.split(protected)
    if len(parts) == 1:
        # Fallback: semicolon clauses if no period split
        parts = re.split(r"\s*;\s+", protected)
    out = [_restore_abbrevs(p.strip(), store) for p in parts if p.strip()]
    return out or [text]


def first_sentence(text: str, max_chars: int = 320) -> str:
    sents = split_sentences(text)
    if not sents:
        return ""
    cut = sents[0]
    if len(cut) <= max_chars:
        return cut
    return cut[:max_chars].rsplit(" ", 1)[0] + "…"


def summarize_article(
    text: str,
    *,
    max_chars: int = 420,
    max_sentences: int = 2,
    lowercase_start: bool = False,
) -> str:
    """Natural short summary: first 1–2 robust sentences, truncated cleanly."""
    sents = split_sentences(text)
    if not sents:
        return snippet(text, max_chars)
    buf: list[str] = []
    total = 0
    for s in sents[:max_sentences]:
        if total and total + len(s) + 1 > max_chars:
            break
        buf.append(s)
        total += len(s) + 1
    out = " ".join(buf) if buf else sents[0]
    if lowercase_start and out:
        out = out[0].lower() + out[1:]
    if len(out) > max_chars:
        return out[:max_chars].rsplit(" ", 1)[0] + "…"
    return out


def snippet(text: str, max_chars: int = 220) -> str:
    text = normalize_ws(text)
    if len(text) <= max_chars:
        return text
    cut = text[:max_chars].rsplit(" ", 1)[0]
    return cut + "…"


def embed_clause(lead: str, clause: str) -> str:
    """Join ``lead`` + clause with French elision (que → qu' before vowel)."""
    if not clause:
        return lead
    body = clause[0].lower() + clause[1:] if clause else clause
    if lead.endswith(" que") and body[:1] in "aeiouàâäéèêëîïôöùûüh":
        return lead[:-4] + " qu'" + body
    return f"{lead} {body}"


def contrast_versions(old_text: str, new_text: str, *, max_chars: int = 220) -> str:
    """One sentence describing how tip differs from historical version."""
    old_s = summarize_article(old_text, max_chars=max_chars, max_sentences=1)
    new_s = summarize_article(new_text, max_chars=max_chars, max_sentences=1)
    if fold(old_s) == fold(new_s):
        return (
            "la rédaction courante a été remaniée (longueur ou formulation différente) "
            "par rapport à la version alors en vigueur"
        )
    return f"aujourd'hui le texte dispose notamment : {new_s}"
