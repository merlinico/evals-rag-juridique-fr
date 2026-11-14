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

# Trailing code qualifier right after the citation span.
_CODE_QUALIFIER = re.compile(
    r"^\s*(?:"
    r"du présent code"
    r"|dudit code"
    r"|du même code"
    r"|des mêmes codes?"
    r"|du code (?P<prep>de la |de l['']|du |des )?(?P<name>[\w'’\-]+(?:\s+[\w'’\-]+){0,4})"
    r"|de ce code"
    r")",
    flags=re.IGNORECASE,
)

_PRIOR_CODE = re.compile(
    r"code\s+(?P<prep>de la |de l['']|du |des )?(?P<name>[\w'’\-]+(?:\s+[\w'’\-]+){0,4})",
    flags=re.IGNORECASE,
)

# Map surface names → snapshot code keys (None = external / not in snapshot).
_CODE_NAME_MAP: dict[str, str | None] = {
    "civil": "civil",
    "la consommation": "consommation",
    "consommation": "consommation",
    "du travail": "travail",
    "travail": "travail",
    "commerce": None,
    "du commerce": None,
    "pénal": None,
    "penal": None,
    "la route": None,
    "la construction": None,
    "la construction et de l habitation": None,
    "la construction et de l'habitation": None,
    "l habitation": None,
    "procédure civile": None,
    "procedure civile": None,
    "procédure pénale": None,
    "procedure penale": None,
    "la santé publique": None,
    "environnement": None,
    "de l environnement": None,
    "monétaire et financier": None,
    "monetaire et financier": None,
    "de l urbanisme": None,
    "urbanisme": None,
}


def _normalize_code_name(raw: str) -> str:
    text = raw.strip().lower().replace("’", "'")
    text = re.sub(r"\s+", " ", text)
    return text


def resolve_code_name(raw: str) -> str | None | object:
    """Return snapshot code key, None if external, or Ellipsis if unknown label."""
    name = _normalize_code_name(raw)
    if name in _CODE_NAME_MAP:
        return _CODE_NAME_MAP[name]
    # Fuzzy contains
    for key, val in _CODE_NAME_MAP.items():
        if key in name or name in key:
            return val
    return Ellipsis


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


def inferred_target_code(
    text: str,
    span_start: int,
    span_end: int,
    source_code: str | None,
) -> str | None | object:
    """Infer the intended code for a citation.

    Returns:
      - snapshot code key (civil / consommation / travail)
      - ``None`` if the citation points to an external code (drop the edge)
      - ``Ellipsis`` if no qualifier → default to source_code
    """
    after = text[span_end : span_end + 90]
    m = _CODE_QUALIFIER.match(after)
    if not m:
        return Ellipsis

    phrase = m.group(0).lower()
    if "présent code" in phrase or "de ce code" in phrase:
        return source_code

    if "dudit code" in phrase or "même code" in phrase or "mêmes code" in phrase:
        # Look backward for the most recent explicit "code de …"
        prior = text[max(0, span_start - 200) : span_start]
        matches = list(_PRIOR_CODE.finditer(prior))
        if not matches:
            return Ellipsis
        name = matches[-1].group("name")
        prep = matches[-1].group("prep") or ""
        return resolve_code_name(f"{prep}{name}".strip())

    name = m.group("name")
    prep = m.group("prep") or ""
    if name:
        return resolve_code_name(f"{prep}{name}".strip())
    return Ellipsis


def build_crossrefs(
    articles: Iterable,
    *,
    num_index: Mapping[tuple[str | None, str], str] | None = None,
) -> list[CrossRef]:
    """Build directed CrossRef edges resolved against an article index.

    ``num_index`` maps ``(code, normalized_num)`` → article id. When absent,
    it is built from ``articles``.

    Citations qualified as belonging to another code (``du code de commerce``,
    ``dudit code`` after a foreign code, etc.) are dropped when they cannot be
    resolved inside the source code.
    """
    arts = list(articles)
    if num_index is None:
        index: dict[tuple[str | None, str], str] = {}
        for a in arts:
            key = (getattr(a, "code", None), normalize_article_num(a.num))
            index.setdefault(key, a.id)
            # Fallback without code only for unqualified citations.
            index.setdefault((None, normalize_article_num(a.num)), a.id)
        num_index = index

    id_to_code = {a.id: getattr(a, "code", None) for a in arts}
    refs: list[CrossRef] = []
    seen_edges: set[tuple[str, str, str]] = set()

    for art in arts:
        code = id_to_code.get(art.id)
        for target_num, start, end, kind in extract_reference_spans(art.text):
            intended = inferred_target_code(art.text, start, end, code)
            if intended is None:
                # Explicit foreign code — do not link inside the snapshot.
                continue
            resolve_code = code if intended is Ellipsis else intended
            target_id = num_index.get((resolve_code, target_num))
            if target_id is None and intended is Ellipsis:
                # Unqualified: allow weak fallback only if same-code candidate exists
                # already tried; never cross-wire via bare (None, num) when a
                # same-code miss would silently pick another code.
                target_id = None
            if not target_id or target_id == art.id:
                continue
            # Guard: never keep an edge whose target code ≠ intended/source.
            tgt_code = id_to_code.get(target_id)
            expected = code if intended is Ellipsis else intended
            if expected is not None and tgt_code != expected:
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


def is_false_cross_code_ref(
    ref: CrossRef,
    *,
    source_text: str,
    source_code: str | None,
    target_code: str | None,
) -> bool:
    """True when an existing edge should be dropped as a foreign-code mislink."""
    if ref.span_start is None or ref.span_end is None:
        # No span: drop cross-code edges conservatively.
        return source_code != target_code
    intended = inferred_target_code(
        source_text, ref.span_start, ref.span_end, source_code
    )
    if intended is None:
        return True
    if intended is Ellipsis:
        return source_code != target_code
    return intended != target_code
