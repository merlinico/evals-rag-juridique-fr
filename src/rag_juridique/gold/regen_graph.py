"""Regenerate multi_hop / temporal questions from full corpus graph.

Uses real ``CrossRef`` edges and ``Corpus.version_at`` so temporal ``as_of``
dates resolve to a version whose text actually differs from the tip.
"""

from __future__ import annotations

import hashlib
import re
from collections import defaultdict
from datetime import date, timedelta
from typing import TYPE_CHECKING

from rag_juridique.contracts.corpus import Article
from rag_juridique.contracts.gold import Question, QuestionType
from rag_juridique.gold.textutil import first_sentence, normalize_ws, snippet

if TYPE_CHECKING:
    from rag_juridique.corpus.loader import Corpus

_NUM_OK = re.compile(r"^(L\.\s*|R\.\s*|D\.\s*)?\d", re.IGNORECASE)
_L_NUM = re.compile(r"^L\.\s*\d", re.IGNORECASE)

# Probe dates for finding a differing historical version.
_PROBE_DATES = [
    date(2012, 1, 1),
    date(2015, 6, 1),
    date(2016, 10, 1),
    date(2018, 1, 1),
    date(2019, 3, 1),
    date(2020, 1, 1),
    date(2021, 1, 1),
    date(2022, 1, 1),
    date(2023, 1, 1),
    date(2024, 1, 1),
]

_MH_PATTERNS = [
    (
        "L'article {src} du Code {code} renvoie à l'article {tgt} : "
        "que dispose {src}, et que précise {tgt} ?"
    ),
    (
        "En combinant les articles {src} et {tgt} ({code}), quelles règles "
        "s'appliquent au renvoi mentionné ?"
    ),
    (
        "Quel est le contenu du renvoi de l'article {src} vers l'article {tgt} "
        "dans le Code {code} ?"
    ),
    (
        "Pour appliquer l'article {src}, faut-il aussi lire l'article {tgt} "
        "({code}) ? Que disent-ils ensemble ?"
    ),
]

_CODE_LABEL = {
    "civil": "civil",
    "consommation": "de la consommation",
    "travail": "du travail",
}


def _stable_int(seed: str) -> int:
    return int(hashlib.sha1(seed.encode("utf-8")).hexdigest()[:8], 16)


def _is_usable_article(art: Article) -> bool:
    if not art.text or len(art.text.strip()) < 100:
        return False
    if not _NUM_OK.match(art.num or ""):
        return False
    low = (art.num or "").lower()
    if "annexe" in low:
        return False
    return True


def _prefer_legislative(art: Article) -> bool:
    return bool(_L_NUM.match(art.num or "")) or (
        art.code == "civil" and (art.num or "").isdigit()
    )


def generate_multi_hop_from_corpus(
    corpus: Corpus,
    *,
    target: int = 40,
    per_code: dict[str, int] | None = None,
) -> list[Question]:
    """Build multi_hop candidates from real CrossRef edges (all three codes)."""
    goals = per_code or {
        "consommation": 16,
        "civil": 12,
        "travail": 12,
    }
    by_id = corpus.by_id()
    buckets: dict[str, list[Question]] = defaultdict(list)
    seen_pairs: set[tuple[str, str]] = set()

    # Prefer renvoi, then explicit_citation; legislative nums first.
    def _ref_rank(r) -> tuple[int, int]:
        src = by_id.get(r.source_article_id)
        return (
            0 if r.kind.value == "renvoi" else 1,
            0 if (src is not None and _prefer_legislative(src)) else 1,
        )

    refs = sorted(corpus.crossrefs, key=_ref_rank)

    for ref in refs:
        src = by_id.get(ref.source_article_id)
        tgt = by_id.get(ref.target_article_id)
        if src is None or tgt is None:
            continue
        if src.id == tgt.id:
            continue
        if not _is_usable_article(src) or not _is_usable_article(tgt):
            continue
        code = src.code or "unknown"
        if code not in goals:
            continue
        if len(buckets[code]) >= goals[code] + 20:  # headroom for filters
            continue
        pair = (src.id, tgt.id)
        if pair in seen_pairs:
            continue
        seen_pairs.add(pair)

        label = _CODE_LABEL.get(code, code)
        tmpl = _MH_PATTERNS[_stable_int(src.id + tgt.id) % len(_MH_PATTERNS)]
        question = tmpl.format(src=src.num, tgt=tgt.num, code=label)
        answer = (
            f"{src.num} ({code}) : {first_sentence(src.text, 180)} "
            f"{tgt.num} : {first_sentence(tgt.text, 180)} "
            f"Le renvoi ({ref.kind.value}) articule les deux dispositions."
        )
        qid = f"mh{_stable_int(src.id + '|' + tgt.id) % 100000:05d}"
        buckets[code].append(
            Question(
                id=qid,
                question=normalize_ws(question),
                type=QuestionType.MULTI_HOP,
                expected_article_ids=[src.id, tgt.id],
                expected_article_nums=[src.num, tgt.num],
                reference_answer=normalize_ws(answer),
                unanswerable=False,
                validated=False,
                topic=f"crossref:{code}:{ref.kind.value}",
                notes=(
                    f"CrossRef réel {ref.kind.value} "
                    f"{src.id}→{tgt.id} (corpus {corpus.snapshot_id})"
                ),
            )
        )

    # Flatten with balanced take
    out: list[Question] = []
    for code, goal in goals.items():
        out.extend(buckets.get(code, [])[:goal])
    # Fill up to target from leftovers
    if len(out) < target:
        leftovers = []
        for code, items in buckets.items():
            leftovers.extend(items[goals.get(code, 0) :])
        for q in leftovers:
            if len(out) >= target:
                break
            if q.id not in {x.id for x in out}:
                out.append(q)
    # Re-id sequentially mh01.. for readability
    renumbered: list[Question] = []
    for i, q in enumerate(out[: max(target, len(out))], start=1):
        renumbered.append(q.model_copy(update={"id": f"mh{i:02d}"}))
    return renumbered[:target]


def _pick_as_of_with_diff(
    corpus: Corpus,
    article_id: str,
    tip_text: str,
) -> tuple[date, object] | None:
    """Return (as_of, ArticleVersion) where version text ≠ tip text."""
    tip_norm = tip_text.strip()
    vers = corpus.versions_for(article_id)
    if len(vers) < 2:
        return None
    for as_of in _PROBE_DATES:
        ver = corpus.version_at(article_id, as_of)
        if ver is None:
            continue
        if ver.text.strip() == tip_norm:
            continue
        # Prefer dates strictly inside the version interval when possible
        if ver.debut and as_of < ver.debut:
            continue
        if ver.fin and as_of >= ver.fin:
            continue
        # Require meaningful textual difference
        if abs(len(ver.text) - len(tip_norm)) < 20 and ver.text.strip()[:80] == tip_norm[:80]:
            # still different somewhere — accept if jaccard-ish length ok
            if ver.text.strip() == tip_norm:
                continue
        return as_of, ver
    # Fallback: mid-point of an older closed version interval.
    closed = [v for v in vers if v.fin is not None and v.debut is not None]
    closed.sort(key=lambda v: v.debut or date.min)
    for ver in closed:
        if ver.text.strip() == tip_norm:
            continue
        assert ver.debut is not None and ver.fin is not None
        if ver.fin <= ver.debut:
            continue
        delta = ver.fin - ver.debut
        as_of = ver.debut + timedelta(days=max(0, delta.days // 2))
        check = corpus.version_at(article_id, as_of)
        if check is None or check.text.strip() == tip_norm:
            continue
        return as_of, check
    return None


def generate_temporal_from_versions(
    corpus: Corpus,
    *,
    target: int = 30,
    per_code: dict[str, int] | None = None,
) -> list[Question]:
    """Temporal questions where ``version_at(as_of)`` text ≠ tip article text."""
    goals = per_code or {
        "consommation": 14,
        "civil": 14,
        "travail": 14,
    }
    # Extra candidates for filters (civil diffs are scarcer).
    headroom = {"consommation": 50, "civil": 80, "travail": 50}
    buckets: dict[str, list[Question]] = defaultdict(list)

    # Prefer legislative / civil numeric articles; shuffle by code affinity.
    articles = [
        a for a in corpus.articles if _is_usable_article(a) and _prefer_legislative(a)
    ]
    articles.sort(
        key=lambda a: (
            0 if a.code == "civil" else 1 if a.code == "consommation" else 2,
            -len(a.text),
            a.id,
        )
    )

    for art in articles:
        code = art.code or "unknown"
        if code not in goals:
            continue
        if len(buckets[code]) >= goals[code] + headroom.get(code, 15):
            continue
        picked = _pick_as_of_with_diff(corpus, art.id, art.text)
        if picked is None:
            continue
        as_of, ver = picked
        # Require a clear textual gap vs tip (not a trivial whitespace change).
        if ver.text.strip()[:120] == art.text.strip()[:120] and abs(
            len(ver.text) - len(art.text)
        ) < 40:
            continue
        label = _CODE_LABEL.get(code, code)
        hist = first_sentence(ver.text, 280)
        tip_snip = first_sentence(art.text, 120)
        variants = [
            (
                f"Selon le droit en vigueur au {as_of.isoformat()}, que disposait "
                f"l'article {art.num} du Code {label} ?"
            ),
            (
                f"Au {as_of.isoformat()}, quelle était la rédaction applicable de "
                f"l'article {art.num} ({label}) ?"
            ),
            (
                f"En date du {as_of.isoformat()}, que prévoyait l'article {art.num} "
                f"du Code {label} ?"
            ),
            (
                f"Quelle règle résultait de l'article {art.num} (Code {label}) "
                f"tel qu'en vigueur le {as_of.isoformat()} ?"
            ),
        ]
        question = variants[_stable_int(art.id + as_of.isoformat()) % len(variants)]
        answer = (
            f"Au {as_of.isoformat()}, l'article {art.num} disposait : {hist} "
            f"(version {ver.version_id} ; rédaction courante différente : "
            f"{snippet(tip_snip, 80)})"
        )
        buckets[code].append(
            Question(
                id=f"t{_stable_int(art.id + as_of.isoformat()) % 100000:05d}",
                question=normalize_ws(question),
                type=QuestionType.TEMPORAL,
                expected_article_ids=[art.id],
                expected_article_nums=[art.num],
                reference_answer=normalize_ws(answer),
                as_of=as_of,
                unanswerable=False,
                validated=False,
                topic=f"temporal:{code}",
                notes=(
                    f"version_at({as_of.isoformat()})={ver.version_id} "
                    f"≠ tip {art.id}; debut={ver.debut} fin={ver.fin}"
                ),
            )
        )

    out: list[Question] = []
    for code, goal in goals.items():
        out.extend(buckets.get(code, [])[:goal])
    if len(out) < target:
        leftovers = []
        for code, items in buckets.items():
            leftovers.extend(items[goals.get(code, 0) :])
        for q in leftovers:
            if len(out) >= target:
                break
            out.append(q)
    renumbered: list[Question] = []
    for i, q in enumerate(out[:target], start=1):
        renumbered.append(q.model_copy(update={"id": f"t{i:02d}"}))
    return renumbered
