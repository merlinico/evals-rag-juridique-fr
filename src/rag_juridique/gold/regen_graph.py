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
    _trim_dangling_ref,
    contrast_versions,
    embed_clause,
    fix_proper_nouns,
    fold,
    is_territorial_renvoi_table,
    normalize_ws,
    safe_clip,
    split_sentences,
    summarize_article,
    versions_are_cosmetic,
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


def _actor_for(code: str, text: str) -> str:
    """Pick a domain-appropriate subject (not always « professionnel »)."""
    low = fold(text)
    if code == "civil":
        if any(k in low for k in ("testament", "legataire", "heritier", "succession")):
            return "Un héritier"
        if any(k in low for k in ("mariage", "epoux", "divorce", "pacs")):
            return "Un époux"
        if any(k in low for k in ("tutelle", "curatelle", "mineur")):
            return "Un tuteur"
        if any(k in low for k in ("notaire", "acte authentique")):
            return "Un notaire"
        return "Un justiciable"
    if code == "travail":
        if any(k in low for k in ("effectif", "licenciement economique", "employeur")):
            return "Un employeur"
        if any(k in low for k in ("representation", "comite social", "delegue")):
            return "Un délégué du personnel"
        return "Un salarié"
    # consommation
    if any(k in low for k in ("amende administrative", "professionnel est tenu")):
        return "Un professionnel"
    if "consommateur" in low:
        return "Un consommateur"
    return "Un acheteur"


def _core_rule(text: str, *, max_chars: int = 260) -> str:
    """One complete normative clause suitable for a synthesized answer."""
    sents = split_sentences(text)
    if not sents:
        return ""
    summary = sents[0]
    if "1°" in summary:
        intro = summary.split("1°", 1)[0].rstrip(" :;,")
        rest = summary.split("1°", 1)[1]
        first_item = rest.split("2°", 1)[0].split(";")[0].rstrip(" ;,")
        if len(intro) >= 40:
            # Chapeau alone if already informative; else chapeau + 1°.
            informative = any(
                k in fold(intro)
                for k in (
                    "mentionn",
                    "prévu",
                    "passible",
                    "interdit",
                    "punie",
                    "dispose",
                    "prend fin",
                    "nul",
                )
            )
            if len(intro) <= max_chars and informative:
                summary = intro
            else:
                summary = f"{intro} : 1° {first_item}".strip()
    if summary and not re.match(r"^[IVXLC]+\.-", summary):
        summary = summary[0].lower() + summary[1:]
    summary = fix_proper_nouns(summary)
    if len(summary) > max_chars:
        summary = safe_clip(summary, max_chars)
    return fix_proper_nouns(_trim_dangling_ref(summary))


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
    actor = _actor_for(src.code or "", src.text + " " + tgt.text)
    src_core = _core_rule(src.text, max_chars=240)
    tgt_core = _core_rule(tgt.text, max_chars=240)
    variants = [
        (
            f"{actor} s'interroge sur l'article {src.num} du Code {label} : "
            f"quelle règle pose-t-il, et que précise l'article {tgt.num} "
            f"auquel il renvoie ?"
        ),
        (
            f"Que doit-on retenir de l'article {src.num} et de l'article {tgt.num} "
            f"du Code {label} lorsqu'ils sont lus ensemble ?"
        ),
        (
            f"L'article {src.num} du Code {label} cite l'article {tgt.num} : "
            f"quelles obligations ou définitions en résultent concrètement "
            f"pour {actor.lower()} ?"
        ),
        (
            f"Pour appliquer l'article {src.num} du Code {label}, "
            f"{actor.lower()} doit-il aussi tenir compte de l'article {tgt.num} ? "
            f"Que dit chacun ?"
        ),
    ]
    # Never use « Un professionnel… » outside consommation.
    if (src.code or "") != "consommation":
        variants = [v for v in variants if "professionnel" not in fold(v)] or variants
    question = variants[_stable_int(src.id + tgt.id) % len(variants)]
    link = "renvoie" if kind == "renvoi" else "cite"
    answer = (
        f"{embed_clause(f'L\'article {src.num} prévoit que', src_core).rstrip('.')}."
        f" Cet article {link} à l'article {tgt.num}, "
        f"{embed_clause('qui dispose que', tgt_core).rstrip('.')}."
        f" Pour répondre à la question, il faut donc combiner ces deux dispositions."
    )
    return normalize_ws(fix_proper_nouns(question)), normalize_ws(
        fix_proper_nouns(answer)
    )


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
        hist_text, max_chars=320, max_sentences=2, lowercase_start=True
    )
    change = contrast_versions(hist_text, tip_text, max_chars=260).rstrip(".")
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
        f"{embed_clause(lead, hist).rstrip('.')}."
        f" Par rapport à la version aujourd'hui en vigueur, {change}."
    )
    return normalize_ws(fix_proper_nouns(question)), normalize_ws(
        fix_proper_nouns(answer)
    )


def _temporal_candidate_ok(art: Article, hist_text: str, tip_text: str) -> bool:
    if is_territorial_renvoi_table(tip_text) or is_territorial_renvoi_table(hist_text):
        return False
    if versions_are_cosmetic(hist_text, tip_text):
        return False
    # Reject near-identical openings that only shuffle a long table body.
    if tip_text.strip()[:180] == hist_text.strip()[:180] and abs(
        len(tip_text) - len(hist_text)
    ) < 120:
        return False
    hist_sum = summarize_article(hist_text, max_chars=320, max_sentences=2)
    tip_sum = summarize_article(tip_text, max_chars=320, max_sentences=2)
    if len(hist_sum) < 50 or len(tip_sum) < 50:
        return False
    # Pure numbering shells (« 1. ») are useless gold.
    if re.fullmatch(r"[IVXLC]+\.-?|\d+\.?", hist_sum.strip()) or re.fullmatch(
        r"[IVXLC]+\.-?|\d+\.?", tip_sum.strip()
    ):
        return False
    return True


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
        if not _temporal_candidate_ok(art, ver.text, art.text):
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
