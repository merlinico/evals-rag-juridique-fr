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
_AMOUNT_RE = re.compile(
    r"\b(\d[\d\s]*(?:[.,]\d+)?)\s*(euros?|€|jours?|mois|ans?|%|pour\s*cent)\b",
    re.I,
)
# Only legislative-style refs (L. 111-4) or explicit « article 1007 ».
_REF_NUM_RE = re.compile(
    r"(?:article\s+)?((?:[LRDA]\.\s*)\d+(?:-\d+)+|\barticle\s+(\d{2,4})\b)",
    re.I,
)

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

# Proper nouns / institutional names restored after forced lowercasing.
_PROPER_FIXES = [
    (re.compile(r"\bfrance compétences\b", re.I), "France compétences"),
    (re.compile(r"\bconseil d'etat\b", re.I), "Conseil d'État"),
    (re.compile(r"\bconseil d'état\b", re.I), "Conseil d'État"),
    (re.compile(r"\bcaisse des dépôts et consignations\b", re.I), "Caisse des dépôts et consignations"),
    (re.compile(r"\bpôle emploi\b", re.I), "Pôle emploi"),
    (re.compile(r"\bfrance travail\b", re.I), "France Travail"),
]


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


def fix_proper_nouns(text: str) -> str:
    out = text
    for pat, repl in _PROPER_FIXES:
        out = pat.sub(repl, out)
    # Collapse accidental double periods (not ellipsis …).
    out = re.sub(r"\.{2,}(?!\.)", ".", out)
    return out


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


def _trim_dangling_ref(text: str) -> str:
    """Avoid endings like « à l'article L. » or « conformité aux. »."""
    # Do NOT strip '.' before cleaning refs — it would turn « L. » into « L ».
    out = text.rstrip(" ,;:—")
    # Drop incomplete article spans at the end (with or without final digits).
    out = re.sub(
        r"(?:,?\s*)?(?:à\s+)?(?:l['’])?articles?\s+[LRDA]\.?(?:\s*\d[\d\-]*)?"
        r"(?:\s+à\s+[LRDA]\.?(?:\s*\d[\d\-]*)?)?\s*$",
        "",
        out,
        flags=re.I,
    )
    out = re.sub(r"\b[LRDA]\.?\s*$", "", out, flags=re.I)
    out = re.sub(
        r"\b(aux|des|les|le|la|du|de|à|a|sur|dans|par|pour|et|ou|mentionnée)\s*$",
        "",
        out,
        flags=re.I,
    )
    return out.rstrip(" ,;:—")


def safe_clip(text: str, max_chars: int) -> str:
    """Clip without ellipsis and without breaking an article reference."""
    text = normalize_ws(text)
    if len(text) <= max_chars:
        return text
    window = text[:max_chars]
    for sep in (". ", "; ", " : ", " — ", ", "):
        idx = window.rfind(sep)
        if idx >= max(50, max_chars // 3):
            piece = _trim_dangling_ref(window[:idx])
            if len(piece) >= 40:
                return piece
    # Back up before an incomplete « article L. … » span.
    m = list(re.finditer(r"articles?\s+[LRDA]\.", window, re.I))
    if m and m[-1].start() >= 40:
        return _trim_dangling_ref(window[: m[-1].start()])
    return _trim_dangling_ref(window.rsplit(" ", 1)[0])


def first_sentence(text: str, max_chars: int = 320) -> str:
    """First complete sentence. Never truncates with « … »."""
    sents = split_sentences(text)
    if not sents:
        return ""
    cut = sents[0]
    if len(cut) <= max_chars:
        return cut
    return safe_clip(cut, max_chars)


def summarize_article(
    text: str,
    *,
    max_chars: int = 420,
    max_sentences: int = 2,
    lowercase_start: bool = False,
) -> str:
    """Natural short summary from complete sentences (no « … » truncation)."""
    sents = split_sentences(text)
    if not sents:
        return normalize_ws(text)[:max_chars]
    buf: list[str] = []
    total = 0
    for s in sents[:max_sentences]:
        if total and total + len(s) + 1 > max_chars:
            break
        buf.append(s)
        total += len(s) + 1
    out = " ".join(buf) if buf else sents[0]
    if lowercase_start and out and not re.match(r"^[IVXLC]+\.-", out):
        out = out[0].lower() + out[1:]
    out = fix_proper_nouns(out)
    if len(out) > max_chars:
        return safe_clip(out, max_chars)
    return out


def snippet(text: str, max_chars: int = 220) -> str:
    """Display excerpt for review markdown (ellipsis allowed here only)."""
    text = normalize_ws(text)
    if len(text) <= max_chars:
        return text
    cut = text[:max_chars].rsplit(" ", 1)[0]
    return cut + "…"


def embed_clause(lead: str, clause: str) -> str:
    """Join ``lead`` + clause with French elision (que → qu' before vowel)."""
    if not clause:
        return lead
    body = clause
    # Keep structural markers like « I.- » intact; otherwise lowercase start.
    if not re.match(r"^[IVXLC]+\.-", body):
        body = body[0].lower() + body[1:]
    body = fix_proper_nouns(body)
    if lead.endswith(" que") and body[:1] in "aeiouàâäéèêëîïôöùûüh":
        return lead[:-4] + " qu'" + body
    return f"{lead} {body}"


def _amount_map(text: str) -> dict[str, str]:
    out: dict[str, str] = {}
    for m in _AMOUNT_RE.finditer(text):
        unit = normalize_ws(m.group(2).lower())
        out[unit] = normalize_ws(m.group(0))
    return out


def _ref_set(text: str) -> set[str]:
    found: set[str] = set()
    for m in _REF_NUM_RE.finditer(text):
        raw = normalize_ws(m.group(1) or m.group(2) or "")
        # Drop bare « article 10 » noise; keep L./R./D. or multi-digit civil nums.
        if re.match(r"^[LRDA]\.", raw, re.I) or (raw.isdigit() and len(raw) >= 3):
            found.add(fold(raw))
    return found


def versions_are_cosmetic(old_text: str, new_text: str) -> bool:
    """True when tip vs historical differ only by whitespace / light punctuation."""
    a = fold(re.sub(r"[^\w]+", " ", old_text))
    b = fold(re.sub(r"[^\w]+", " ", new_text))
    if a == b:
        return True
    return jaccard(tokens(old_text), tokens(new_text)) >= 0.97


def is_territorial_renvoi_table(text: str) -> bool:
    """Wallis/Mayotte-style applicability tables — not useful temporal gold."""
    head = text[:900]
    return bool(
        re.search(
            r"tableau ci-apr[eè]s|ARTICLES APPLICABLES|"
            r"îles Wallis|Wallis et Futuna|Saint-Pierre-et-Miquelon|"
            r"Nouvelle-Cal[eé]donie|Mayotte|"
            r"collectivit[eé]s? d'outre-mer|"
            r"applicables? (?:dans|à) (?:les îles |Mayotte|Wallis)|"
            r"dans leur r[eé]daction indiqu[eé]e dans la colonne",
            head,
            re.I,
        )
    )


def _shared_prefix_len(a: str, b: str) -> int:
    n = min(len(a), len(b))
    i = 0
    while i < n and a[i] == b[i]:
        i += 1
    return i


def _span_at(text: str, index: int, *, back: int = 40, ahead: int = 180) -> str:
    """Extract a readable span around ``index``, snapped to word boundaries."""
    start = max(0, index - back)
    end = min(len(text), index + ahead)
    if start > 0:
        sp = text.find(" ", start)
        if sp != -1 and sp < index:
            start = sp + 1
    if end < len(text):
        sp = text.rfind(" ", index, end)
        if sp != -1:
            end = sp
    return normalize_ws(text[start:end]).strip(" ,;:«»\"")


def describe_text_edit(old: str, new: str, *, max_chars: int = 220) -> str | None:
    """Focus on the first divergent span when two long clauses share a prefix."""
    old_n, new_n = normalize_ws(old), normalize_ws(new)
    if fold(old_n) == fold(new_n):
        return None
    i = _shared_prefix_len(old_n, new_n)
    if i < 30:
        return None
    old_span = safe_clip(_span_at(old_n, i), min(140, max_chars))
    new_span = safe_clip(_span_at(new_n, i, ahead=max_chars), max_chars)
    if not old_span or not new_span or fold(old_span) == fold(new_span):
        return None
    return fix_proper_nouns(
        f"la version courante modifie le passage « {new_span} » "
        f"(auparavant : « {old_span} »)"
    )


def contrast_versions(old_text: str, new_text: str, *, max_chars: int = 280) -> str:
    """Describe a concrete tip-vs-history change (no vague « remaniée » fallback)."""
    old_text = normalize_ws(old_text)
    new_text = normalize_ws(new_text)

    old_am = _amount_map(old_text)
    new_am = _amount_map(new_text)
    amount_bits: list[str] = []
    for unit, new_val in new_am.items():
        old_val = old_am.get(unit)
        if old_val and fold(old_val) != fold(new_val):
            amount_bits.append(f"le quantum passe de {old_val} à {new_val}")
        elif not old_val:
            amount_bits.append(f"apparaît notamment {new_val}")
    for unit, old_val in old_am.items():
        if unit not in new_am:
            amount_bits.append(f"disparaît notamment {old_val}")
    if amount_bits:
        return fix_proper_nouns(amount_bits[0])

    old_sents = split_sentences(old_text)
    new_sents = split_sentences(new_text)
    old_fold = {fold(s) for s in old_sents}
    new_fold = {fold(s) for s in new_sents}
    added = [s for s in new_sents if fold(s) not in old_fold]
    removed = [s for s in old_sents if fold(s) not in new_fold]

    if added and not removed:
        clause = summarize_article(added[0], max_chars=max_chars, max_sentences=1, lowercase_start=True)
        return fix_proper_nouns(f"la version courante ajoute notamment que {clause}".rstrip("."))
    if removed and not added:
        clause = summarize_article(removed[0], max_chars=max_chars, max_sentences=1, lowercase_start=True)
        return fix_proper_nouns(f"la version courante ne reprend plus la disposition selon laquelle {clause}".rstrip("."))
    if added and removed:
        focused = describe_text_edit(removed[0], added[0], max_chars=max_chars)
        if focused:
            return focused
        tip = summarize_article(added[0], max_chars=max_chars, max_sentences=1, lowercase_start=True).rstrip(".")
        old = summarize_article(removed[0], max_chars=min(160, max_chars), max_sentences=1, lowercase_start=True).rstrip(".")
        if fold(tip) != fold(old) and len(old) >= 24 and len(tip) >= 24:
            return fix_proper_nouns(
                f"là où le texte prévoyait que {old}, la version courante dispose que {tip}"
            )

    old_refs = _ref_set(old_text)
    new_refs = _ref_set(new_text)
    added_refs = sorted(new_refs - old_refs)
    removed_refs = sorted(old_refs - new_refs)
    if added_refs or removed_refs:
        bits: list[str] = []
        if added_refs:
            bits.append("ajout de renvois (" + ", ".join(added_refs[:3]) + ")")
        if removed_refs:
            bits.append("suppression de renvois (" + ", ".join(removed_refs[:3]) + ")")
        return "les renvois internes évoluent : " + " ; ".join(bits)

    # Structural markers (I.- / II.-) even if token overlap is high.
    if bool(re.search(r"\bI\.-", new_text)) != bool(re.search(r"\bI\.-", old_text)):
        tip = summarize_article(new_text, max_chars=max_chars, max_sentences=1, lowercase_start=True)
        return fix_proper_nouns(
            f"la structure du texte a été réécrite ; aujourd'hui il dispose notamment que {tip}".rstrip(".")
        )

    tip = summarize_article(new_text, max_chars=max_chars, max_sentences=1, lowercase_start=True).rstrip(".")
    hist = summarize_article(old_text, max_chars=min(160, max_chars), max_sentences=1, lowercase_start=True).rstrip(".")
    if fold(tip) != fold(hist) and len(hist) >= 40 and len(tip) >= 40:
        return fix_proper_nouns(
            f"là où le texte prévoyait que {hist}, la version courante dispose que {tip}"
        )
    # Last resort: length / wording without the banned vague formula.
    if len(new_text) > len(old_text) + 80:
        return "la version courante développe le dispositif (dispositions supplémentaires)"
    if len(old_text) > len(new_text) + 80:
        return "la version courante simplifie le dispositif (dispositions retirées ou condensées)"
    return "la version courante reformule le dispositif sur le fond (champ, conditions ou effets)"
