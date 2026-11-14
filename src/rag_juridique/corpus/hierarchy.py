"""Parse LEGI contexte paths into livre / titre / chapitre / section."""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class Hierarchy:
    livre: str | None = None
    titre: str | None = None
    chapitre: str | None = None
    section: str | None = None


def _is_kind(part: str, kind: str) -> bool:
    p = part.strip()
    return bool(re.match(rf"^{kind}\b", p, flags=re.IGNORECASE))


def parse_contexte(contexte: str | None) -> Hierarchy:
    """Extract hierarchy levels from a LEGI `texte_contexte` path.

    Section is returned for callers that need it; the frozen ``Article``
    model only stores livre / titre / chapitre (section stays in ``contexte``).
    """
    if not contexte or not contexte.strip():
        return Hierarchy()

    parts = [p.strip() for p in contexte.split(">") if p.strip()]
    livre = titre = chapitre = section = None
    for part in parts:
        if livre is None and _is_kind(part, "Livre"):
            livre = part
        elif titre is None and _is_kind(part, "Titre"):
            titre = part
        elif chapitre is None and _is_kind(part, "Chapitre"):
            chapitre = part
        elif section is None and _is_kind(part, "Section"):
            section = part
    return Hierarchy(livre=livre, titre=titre, chapitre=chapitre, section=section)


def normalize_article_num(num: str | None) -> str:
    """Normalize surface forms like ``L111-1`` / ``L.111-1`` → ``L. 111-1``."""
    raw = (num or "").strip()
    if not raw:
        return ""
    m = re.match(
        r"^([LRDA])\.?\s*([0-9]+(?:-[0-9]+)*(?:\s*bis|\s*ter|\s*quater)?)$",
        raw,
        flags=re.IGNORECASE,
    )
    if m:
        letter = m.group(1).upper()
        rest = re.sub(r"\s+", " ", m.group(2).strip())
        return f"{letter}. {rest}"
    # Code civil style: bare numbers, optionally with bis/ter
    m2 = re.match(
        r"^([0-9]+(?:-[0-9]+)*)(\s*(?:bis|ter|quater))?$",
        raw,
        flags=re.IGNORECASE,
    )
    if m2:
        suffix = (m2.group(2) or "").strip().lower()
        return f"{m2.group(1)}{(' ' + suffix) if suffix else ''}"
    return re.sub(r"\s+", " ", raw)
