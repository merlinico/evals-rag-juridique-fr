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
from rag_juridique.corpus.refs import is_false_cross_code_ref
from rag_juridique.gold.textutil import (
    contrast_versions,
    embed_clause,
    normalize_ws,
    summarize_article,
)

if TYPE_CHECKING:
    from rag_juridique.corpus.loader import Corpus

_NUM_OK = re.compile(r"^(L\.\s*|R\.\s*|D\.\s*)?\d", re.IGNORECASE)
_L_NUM = re.compile(r"^L\.\s*\d", re.IGNORECASE)

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


def _natural_multi_hop_qa(
    src: Article,
    tgt: Article,
    *,
    kind: str,
) -> tuple[str, str]:
    label = _CODE_LABEL.get(src.code or "", src.code or "")
    src_sum = summarize_article(
        src.text, max_chars=280, max_sentences=2, lowercase_start=True
    )
    tgt_sum = summarize_article(
        tgt.text, max_chars=280, max_sentences=2, lowercase_start=True
    )
    variants = [
        (
            f"Un professionnel se prévaut de l'article {src.num} du Code {label} : "
            f"quelle règle trouve-t-on dans cet article, et que précise l'article "
            f"{tgt.num} auquel il renvoie ?"
        ),
        (
            f"Que doit-on retenir de l'article {src.num} et de l'article {tgt.num} "
            f"du Code {label} lorsqu'ils sont lus ensemble ?"
        ),
        (
            f"L'article {src.num} du Code {label} cite l'article {tgt.num} : "
            f"quelles obligations ou définitions en résultent concrètement ?"
        ),
        (
            f"Pour savoir ce que prévoit l'article {src.num} du Code {label}, "
            f"faut-il aussi appliquer l'article {tgt.num} ? Que dit chacun ?"
        ),
    ]
    question = variants[_stable_int(src.id + tgt.id) % len(variants)]
    link = (
        "renvoie expressément"
        if kind == "renvoi"
        else "cite"
    )
    lead_src = f"L'article {src.num} dispose que"
    answer = (
        f"{embed_clause(lead_src, src_sum)} "
        f"Il {link} à l'article {tgt.num}, qui "
        f"{embed_clause('prévoit que', tgt_sum)} "
        f"Les deux textes se complètent : le second précise le régime auquel "
        f"le premier renvoie."
    )
    return normalize_ws(question), normalize_ws(answer)


def generate_multi_hop_from_corpus(
    corpus: Corpus,
    *,
    target: int = 40,
    per_code: dict[str, int] | None = None,
) -> list[Question]:
    """Build multi_hop candidates from real same-code CrossRef edges."""
    goals = per_code or {
        "consommation": 14,
        "civil": 13,
        "travail": 13,
    }
    by_id = corpus.by_id()
    buckets: dict[str, list[Question]] = defaultdict(list)
    seen_pairs: set[tuple[str, str]] = set()

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
        if src.id == tgt.id or src.code != tgt.code:
            continue
        if is_false_cross_code_ref(
            ref,
            source_text=src.text,
            source_code=src.code,
            target_code=tgt.code,
        ):
            continue
        if not _is_usable_article(src) or not _is_usable_article(tgt):
            continue
        code = src.code or "unknown"
        if code not in goals:
            continue
        if len(buckets[code]) >= goals[code] + 25:
            continue
        pair = (src.id, tgt.id)
        if pair in seen_pairs:
            continue
        seen_pairs.add(pair)

        question, answer = _natural_multi_hop_qa(src, tgt, kind=ref.kind.value)
        qid = f"mh{_stable_int(src.id + '|' + tgt.id) % 100000:05d}"
        buckets[code].append(
            Question(
                id=qid,
                question=question,
                type=QuestionType.MULTI_HOP,
                expected_article_ids=[src.id, tgt.id],
                expected_article_nums=[src.num, tgt.num],
                reference_answer=answer,
                unanswerable=False,
                validated=False,
                topic=f"crossref:{code}:{ref.kind.value}",
                notes=(
                    f"CrossRef réel {ref.kind.value} "
                    f"{src.id}→{tgt.id} (corpus {corpus.snapshot_id})"
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
            if q.id not in {x.id for x in out}:
                out.append(q)
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
        if ver.debut and as_of < ver.debut:
            continue
        if ver.fin and as_of >= ver.fin:
            continue
        if ver.text.strip() == tip_norm:
            continue
        return as_of, ver
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


def _natural_temporal_qa(
    art: Article,
    as_of: date,
    hist_text: str,
    tip_text: str,
) -> tuple[str, str]:
    label = _CODE_LABEL.get(art.code or "", art.code or "")
    hist = summarize_article(
        hist_text, max_chars=360, max_sentences=2, lowercase_start=True
    )
    change = contrast_versions(hist_text, tip_text, max_chars=240)
    variants = [
        (
            f"Au {as_of.isoformat()}, quelle règle résultait de l'article "
            f"{art.num} du Code {label} ?"
        ),
        (
            f"Selon le droit applicable le {as_of.isoformat()}, que prévoyait "
            f"l'article {art.num} (Code {label}) ?"
        ),
        (
            f"Que disait l'article {art.num} du Code {label} en vigueur au "
            f"{as_of.isoformat()} ?"
        ),
    ]
    question = variants[_stable_int(art.id + as_of.isoformat()) % len(variants)]
    lead = f"Au {as_of.isoformat()}, l'article {art.num} prévoyait que"
    answer = (
        f"{embed_clause(lead, hist)} "
        f"Par rapport à la version aujourd'hui en vigueur, {change}."
    )
    return normalize_ws(question), normalize_ws(answer)


def generate_temporal_from_versions(
    corpus: Corpus,
    *,
    target: int = 30,
    per_code: dict[str, int] | None = None,
) -> list[Question]:
    """Temporal questions where ``version_at(as_of)`` text ≠ tip article text."""
    goals = per_code or {
        "consommation": 10,
        "civil": 10,
        "travail": 10,
    }
    headroom = {"consommation": 50, "civil": 80, "travail": 50}
    buckets: dict[str, list[Question]] = defaultdict(list)

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
        if ver.text.strip()[:120] == art.text.strip()[:120] and abs(
            len(ver.text) - len(art.text)
        ) < 40:
            continue
        question, answer = _natural_temporal_qa(art, as_of, ver.text, art.text)
        buckets[code].append(
            Question(
                id=f"t{_stable_int(art.id + as_of.isoformat()) % 100000:05d}",
                question=question,
                type=QuestionType.TEMPORAL,
                expected_article_ids=[art.id],
                expected_article_nums=[art.num],
                reference_answer=answer,
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
