"""Apply REVIEW_BATCH blocking fixes: unanswerables, ac05, then regen graph Qs."""

from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path

from rag_juridique.contracts.gold import GoldSet, Question, QuestionType
from rag_juridique.corpus.loader import load_corpus
from rag_juridique.gold.filters import (
    filter_candidates,
    make_version_text_resolver,
)
from rag_juridique.gold.loader import load_gold_set
from rag_juridique.gold.regen_graph import (
    _natural_multi_hop_qa,
    _natural_temporal_qa,
    _temporal_candidate_ok,
    generate_multi_hop_from_corpus,
    generate_temporal_from_versions,
)
from rag_juridique.gold.review import (
    SAMPLE_TO_REVIEW_IDS,
    select_review_batch,
    write_review_batch,
)
from rag_juridique.gold.textutil import fold, jaccard, tokens

ROOT = Path(__file__).resolve().parents[3]
GOLD_PATH = ROOT / "data" / "gold" / "questions.json"
STATS_PATH = ROOT / "data" / "gold" / "filter_stats.json"
REVIEW_PATH = ROOT / "data" / "gold" / "REVIEW_BATCH_40.md"

KEEP_TYPES = {
    QuestionType.DIRECT,
    QuestionType.UNANSWERABLE,
    QuestionType.APPARENT_CONTRADICTION,
}

# Known mappings when an "unanswerable" is now covered by the snapshot.
_REQUALIFY = {
    "u02": {
        "code": "travail",
        "num": "L. 3141-3",
        "question": (
            "Combien de jours de congés payés un salarié acquiert-il par mois de "
            "travail effectif chez le même employeur ?"
        ),
        "answer": (
            "Le salarié a droit à un congé de deux jours et demi ouvrables par mois "
            "de travail effectif chez le même employeur ; la durée totale exigible "
            "ne peut excéder trente jours ouvrables (article L. 3141-3 du Code du travail)."
        ),
        "topic": "congés payés",
    },
}

_AC05 = Question(
    id="ac05",
    question=(
        "L. 121-1 interdit les pratiques commerciales déloyales à l'égard des "
        "consommateurs, tandis que L. 121-5 étend L. 121-2 à L. 121-4 aux pratiques "
        "qui visent les professionnels et les non-professionnels : y a-t-il "
        "contradiction sur le champ d'application ?"
    ),
    type=QuestionType.APPARENT_CONTRADICTION,
    expected_article_ids=["LEGIARTI000032227301", "LEGIARTI000034072564"],
    expected_article_nums=["L. 121-1", "L. 121-5"],
    reference_answer=(
        "Non : L. 121-1 définit et interdit les pratiques déloyales visant le "
        "consommateur ; L. 121-5 ne requalifie pas toute pratique conforme à "
        "L. 121-2 à L. 121-4 en pratique déloyale, il étend seulement le régime "
        "des articles L. 121-2 à L. 121-4 aux pratiques qui visent les "
        "professionnels et les non-professionnels. Les deux textes ont des "
        "champs distincts et s'articulent."
    ),
    unanswerable=False,
    validated=False,
    topic="déloyale champ L.121-5",
    notes="Corrigé : L. 121-5 = extension aux professionnels / non-professionnels",
)


# Domains that belong to the snapshot — if an unanswerable is clearly about
# these, it must be requalified or replaced.
_IN_CORPUS_DOMAIN = re.compile(
    r"\b(cong[eé]s?\s+pay[eé]s|code\s+du\s+travail|code\s+civil|"
    r"code\s+de\s+la\s+consommation|salari[eé]|licenciement|"
    r"contrat\s+de\s+travail|consommateur|clause\s+abusive|"
    r"r[eé]tractation|garantie\s+l[eé]gale)\b",
    re.I,
)


def scan_unanswerables_against_corpus(
    questions: list[Question],
    corpus,
    *,
    jaccard_threshold: float = 0.32,
) -> list[tuple[Question, str, float]]:
    """Return (question, article_id, score) for unanswerables that look covered.

    A hit requires either an explicit in-corpus domain cue, or a high lexical
    overlap with a snapshot article (avoids generic false positives like
    « délai » / « recours »).
    """
    hits: list[tuple[Question, str, float]] = []
    for q in questions:
        if q.type != QuestionType.UNANSWERABLE and not q.unanswerable:
            continue
        q_tok = tokens(q.question)
        if not q_tok:
            continue
        domain_hit = bool(_IN_CORPUS_DOMAIN.search(q.question))
        best_id = ""
        best = 0.0
        for art in corpus.articles:
            art_fold = fold(art.text)
            if not any(t in art_fold for t in list(q_tok)[:8]):
                continue
            score = jaccard(q_tok, tokens(art.text))
            if score > best:
                best = score
                best_id = art.id
        thr = 0.22 if domain_hit else jaccard_threshold
        if best >= thr and best_id:
            hits.append((q, best_id, best))
        elif domain_hit:
            # Domain cue alone is enough to flag (e.g. u02 before requalify).
            hits.append((q, best_id or "domain_cue", best))
    return hits


def requalify_u02(questions: list[Question], corpus) -> list[str]:
    """Convert u02 to direct with L. 3141-3 gold. Returns list of changed ids."""
    changed: list[str] = []
    by_num = corpus.by_num("travail")
    spec = _REQUALIFY["u02"]
    art = by_num.get(spec["num"])
    if art is None:
        raise RuntimeError(f"Missing {spec['num']} in travail corpus")
    out: list[Question] = []
    for q in questions:
        if q.id != "u02":
            out.append(q)
            continue
        out.append(
            Question(
                id="u02",
                question=spec["question"],
                type=QuestionType.DIRECT,
                expected_article_ids=[art.id],
                expected_article_nums=[art.num],
                reference_answer=spec["answer"],
                unanswerable=False,
                validated=False,
                topic=spec["topic"],
                notes="Requalifié : Code du travail désormais dans le snapshot",
            )
        )
        changed.append("u02")
    return changed


def apply_ac05_fix(questions: list[Question]) -> list[str]:
    changed: list[str] = []
    out: list[Question] = []
    for q in questions:
        if q.id != "ac05":
            out.append(q)
            continue
        out.append(_AC05)
        changed.append("ac05")
    # mutate list in place via return of new list — caller replaces
    questions[:] = out
    return changed


def replace_leaking_unanswerables(
    questions: list[Question],
    leaks: list[tuple[Question, str, float]],
    corpus,
) -> list[str]:
    """Replace remaining leaks with clearly out-of-domain unanswerables."""
    leak_ids = {q.id for q, _, _ in leaks if q.id != "u02"}
    if not leak_ids:
        return []
    replacements = [
        (
            "Quel est le quantum de la peine d'emprisonnement encourue pour un "
            "assassinat selon le Code pénal ?"
        ),
        (
            "Quel est le montant du droit de timbre pour une requête devant le "
            "Conseil d'État en matière fiscale ?"
        ),
        (
            "Quelle majorité est requise au Congrès pour réviser la Constitution "
            "sans référendum ?"
        ),
        (
            "Quel est le délai de prescription de l'action publique pour un crime "
            "de droit commun au sens du Code de procédure pénale ?"
        ),
        (
            "Quelle est la distance minimale de plantation d'arbres de haute tige "
            "par rapport à la limite séparative selon le Code rural ?"
        ),
        (
            "Quel est le taux de la taxe sur la valeur ajoutée applicable aux "
            "médicaments remboursables en France métropolitaine ?"
        ),
        (
            "Qui nomme le Premier président de la Cour de cassation ?"
        ),
        (
            "Quel est le plafond d'émission d'un livret d'épargne populaire ?"
        ),
    ]
    changed: list[str] = []
    rep_i = 0
    out: list[Question] = []
    for q in questions:
        if q.id not in leak_ids:
            out.append(q)
            continue
        text = replacements[rep_i % len(replacements)]
        rep_i += 1
        out.append(
            Question(
                id=q.id,
                question=text,
                type=QuestionType.UNANSWERABLE,
                expected_article_ids=[],
                expected_article_nums=[],
                reference_answer="je ne sais pas",
                unanswerable=True,
                validated=False,
                topic="hors corpus (contrôle auto post-élargissement)",
                notes="Remplacé car l'ancienne formulation était désormais couverte",
            )
        )
        changed.append(q.id)
    questions[:] = out
    return changed


def run_fixes(*, dry_run: bool = False) -> dict:
    corpus = load_corpus()
    gold = load_gold_set(GOLD_PATH)
    questions = list(gold.questions)
    changed_ids: list[str] = []

    # 1) ac05
    changed_ids.extend(apply_ac05_fix(questions))

    # 2) u02 requalify
    # mutate via rebuild
    tmp: list[Question] = []
    by_num = corpus.by_num("travail")
    art = by_num["L. 3141-3"]
    for q in questions:
        if q.id != "u02":
            tmp.append(q)
            continue
        tmp.append(
            Question(
                id="u02",
                question=_REQUALIFY["u02"]["question"],
                type=QuestionType.DIRECT,
                expected_article_ids=[art.id],
                expected_article_nums=[art.num],
                reference_answer=_REQUALIFY["u02"]["answer"],
                unanswerable=False,
                validated=False,
                topic="congés payés",
                notes="Requalifié : Code du travail désormais dans le snapshot",
            )
        )
        changed_ids.append("u02")
    questions = tmp

    # 3) scan remaining unanswerables
    leaks = scan_unanswerables_against_corpus(questions, corpus)
    leak_report = [
        {"id": q.id, "article_id": aid, "score": round(score, 3)}
        for q, aid, score in leaks
    ]
    changed_ids.extend(replace_leaking_unanswerables(questions, leaks, corpus))

    # 4) keep non-graph types, regen mh/temporal
    kept = [
        q
        for q in questions
        if q.type in KEEP_TYPES or q.id == "q26"
    ]
    # Drop old mh/t (except q26)
    # already filtered by KEEP_TYPES + q26

    mh_raw = generate_multi_hop_from_corpus(corpus, target=55)
    mh_slots = 40 - (1 if any(q.id == "q26" for q in kept) else 0)
    t_raw = generate_temporal_from_versions(corpus, target=55)

    resolver = make_version_text_resolver(corpus)
    mh_kept, mh_stats = filter_candidates(
        mh_raw,
        corpus.articles,
        gold_text_resolver=resolver,
        existing_for_dedup=kept,
        dedup_threshold=0.88,
    )
    t_kept, t_stats = filter_candidates(
        t_raw,
        corpus.articles,
        gold_text_resolver=resolver,
        existing_for_dedup=kept + mh_kept,
        dedup_threshold=0.90,
    )
    mh_renum = [
        q.model_copy(update={"id": f"mh{i:02d}"})
        for i, q in enumerate(mh_kept[:mh_slots], start=1)
    ]
    t_renum = [
        q.model_copy(update={"id": f"t{i:02d}"})
        for i, q in enumerate(t_kept[:30], start=1)
    ]
    changed_ids.extend([q.id for q in mh_renum])
    changed_ids.extend([q.id for q in t_renum])

    combined = kept + mh_renum + t_renum
    # Ensure no unanswerable still leaks
    leaks_final = scan_unanswerables_against_corpus(combined, corpus)
    if leaks_final:
        replace_leaking_unanswerables(combined, leaks_final, corpus)
        changed_ids.extend([q.id for q, _, _ in leaks_final])

    gold_out = GoldSet(
        version="0.3.1",
        corpus_snapshot=corpus.snapshot_id,
        language="fr",
        validated=False,
        notes=(
            "Gold v0.3.1 — correctifs revue REVIEW_BATCH : réponses mh/temporal "
            "robustes, CrossRef hors-code filtrés, u02 requalifié, ac05 corrigé, "
            "batch rééquilibré civil/travail. validated=false."
        ),
        questions=combined,
    )

    batch = select_review_batch(combined, size=40, must_include=SAMPLE_TO_REVIEW_IDS)
    # Drop u02 from SAMPLE if still listed as unanswerable sample — SAMPLE has u01/u05 only.

    stats = {
        "mode": "review_fixes_v031",
        "corpus_snapshot": corpus.snapshot_id,
        "n_articles": len(corpus.articles),
        "n_crossrefs": len(corpus.crossrefs),
        "multi_hop_filter": mh_stats.as_dict(),
        "temporal_filter": t_stats.as_dict(),
        "candidates_in": mh_stats.candidates_in + t_stats.candidates_in,
        "kept": mh_stats.kept + t_stats.kept,
        "rejected_answerability": (
            mh_stats.rejected_answerability + t_stats.rejected_answerability
        ),
        "rejected_dedup": mh_stats.rejected_dedup + t_stats.rejected_dedup,
        "rejected_leakage": mh_stats.rejected_leakage + t_stats.rejected_leakage,
        "rejected_schema": mh_stats.rejected_schema + t_stats.rejected_schema,
        "rejection_rate": round(
            1.0
            - (
                (mh_stats.kept + t_stats.kept)
                / max(1, mh_stats.candidates_in + t_stats.candidates_in)
            ),
            4,
        ),
        "selected_total": len(combined),
        "selected_by_type": dict(Counter(q.type.value for q in combined)),
        "multi_hop_by_code": dict(
            Counter(
                (q.topic or "").split(":")[1]
                for q in mh_renum
                if q.topic and q.topic.startswith("crossref:")
            )
        ),
        "temporal_by_code": dict(
            Counter(
                (q.topic or "").split(":")[1]
                for q in t_renum
                if q.topic and q.topic.startswith("temporal:")
            )
        ),
        "review_batch_ids": [q.id for q in batch],
        "review_batch_by_type": dict(Counter(q.type.value for q in batch)),
        "review_batch_codes_mh_t": {
            q.id: (q.topic or "")
            for q in batch
            if q.type in (QuestionType.MULTI_HOP, QuestionType.TEMPORAL)
        },
        "changed_ids": sorted(set(changed_ids)),
        "unanswerable_leak_scan": leak_report,
        "unanswerable_leaks_remaining": [
            {"id": q.id, "article_id": aid, "score": round(s, 3)}
            for q, aid, s in scan_unanswerables_against_corpus(combined, corpus)
        ],
    }

    if dry_run:
        return stats

    GOLD_PATH.write_text(
        json.dumps(gold_out.model_dump(mode="json"), ensure_ascii=False, indent=2)
        + "\n",
        encoding="utf-8",
    )
    STATS_PATH.write_text(
        json.dumps(stats, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    note = (
        "> **Correctifs revue (v0.3.1)** : réponses mh/temporal réécrites ; "
        "CrossRef hors-code filtrés ; `u02` requalifié en direct (L. 3141-3) ; "
        "`ac05` corrigé ; batch rééquilibré civil / travail / consommation."
    )
    write_review_batch(REVIEW_PATH, batch, corpus.articles, header_note=note)
    return stats


def _mh_kind(topic: str | None) -> str:
    if topic and topic.endswith(":renvoi"):
        return "renvoi"
    return "citation"


def run_quality_pass(*, dry_run: bool = False) -> dict:
    """Second-pass quality rewrite: keep IDs, fix answers/questions in place."""
    corpus = load_corpus()
    gold = load_gold_set(GOLD_PATH)
    by_id = corpus.by_id()
    questions = list(gold.questions)
    changed: list[dict] = []
    used_temporal_arts: set[str] = set()

    for q in questions:
        if q.type == QuestionType.TEMPORAL and q.expected_article_ids:
            used_temporal_arts.add(q.expected_article_ids[0])

    # Pool of fresh substantive temporal candidates by code.
    t_pool = generate_temporal_from_versions(corpus, target=120)
    pool_by_code: dict[str, list[Question]] = {}
    for cand in t_pool:
        code = (cand.topic or "").split(":")[-1]
        pool_by_code.setdefault(code, []).append(cand)

    out: list[Question] = []
    for q in questions:
        if q.type == QuestionType.MULTI_HOP and q.id != "q26":
            if len(q.expected_article_ids) < 2:
                out.append(q)
                continue
            src = by_id.get(q.expected_article_ids[0])
            tgt = by_id.get(q.expected_article_ids[1])
            if src is None or tgt is None:
                out.append(q)
                continue
            question, answer = _natural_multi_hop_qa(
                src, tgt, kind=_mh_kind(q.topic)
            )
            before = {
                "question": q.question,
                "answer": q.reference_answer,
            }
            new_q = q.model_copy(
                update={
                    "question": question,
                    "reference_answer": answer,
                    "validated": False,
                    "notes": (q.notes or "") + " | quality-pass v0.3.2",
                }
            )
            out.append(new_q)
            changed.append(
                {
                    "id": q.id,
                    "action": "rewrite_multi_hop",
                    "before_q": before["question"],
                    "after_q": question,
                    "before_a": before["answer"],
                    "after_a": answer,
                }
            )
            continue

        if q.type == QuestionType.TEMPORAL:
            art = by_id.get(q.expected_article_ids[0]) if q.expected_article_ids else None
            if art is None or q.as_of is None:
                out.append(q)
                continue
            ver = corpus.version_at(art.id, q.as_of)
            hist = ver.text if ver is not None else ""
            tip = art.text
            # Replace only non-substantive / territorial-table items.
            # Vague « remaniée » answers are rewritten in place when the diff is real.
            replace = ver is None or not _temporal_candidate_ok(art, hist, tip)
            if not replace:
                question, answer = _natural_temporal_qa(art, q.as_of, hist, tip)
                if "…" in answer or "remaniée" in answer:
                    replace = True
                else:
                    before = {"question": q.question, "answer": q.reference_answer}
                    new_q = q.model_copy(
                        update={
                            "question": question,
                            "reference_answer": answer,
                            "validated": False,
                            "notes": (q.notes or "") + " | quality-pass v0.3.2",
                        }
                    )
                    out.append(new_q)
                    changed.append(
                        {
                            "id": q.id,
                            "action": "rewrite_temporal",
                            "article": art.num,
                            "before_q": before["question"],
                            "after_q": question,
                            "before_a": before["answer"],
                            "after_a": answer,
                        }
                    )
                    continue

            code = art.code or "consommation"
            replacement: Question | None = None
            for cand in pool_by_code.get(code, []):
                cid = cand.expected_article_ids[0]
                if cid in used_temporal_arts:
                    continue
                cart = by_id[cid]
                cver = corpus.version_at(cid, cand.as_of) if cand.as_of else None
                if cver is None or cand.as_of is None:
                    continue
                if not _temporal_candidate_ok(cart, cver.text, cart.text):
                    continue
                used_temporal_arts.add(cid)
                used_temporal_arts.discard(art.id)
                question, answer = _natural_temporal_qa(
                    cart, cand.as_of, cver.text, cart.text
                )
                replacement = q.model_copy(
                    update={
                        "question": question,
                        "reference_answer": answer,
                        "expected_article_ids": [cart.id],
                        "expected_article_nums": [cart.num],
                        "as_of": cand.as_of,
                        "topic": f"temporal:{code}",
                        "validated": False,
                        "notes": (
                            f"quality-pass v0.3.2 replace {art.num}→{cart.num}; "
                            f"version_at({cand.as_of.isoformat()})={cver.version_id}"
                        ),
                    }
                )
                changed.append(
                    {
                        "id": q.id,
                        "action": "replace_temporal",
                        "from_article": art.num,
                        "to_article": cart.num,
                        "as_of": cand.as_of.isoformat(),
                        "before_q": q.question,
                        "after_q": question,
                        "before_a": q.reference_answer,
                        "after_a": answer,
                    }
                )
                break
            if replacement is None:
                # Fallback: rewrite anyway with improved contrast.
                if ver is not None and q.as_of is not None:
                    question, answer = _natural_temporal_qa(art, q.as_of, hist, tip)
                    out.append(
                        q.model_copy(
                            update={
                                "question": question,
                                "reference_answer": answer,
                                "validated": False,
                                "notes": (q.notes or "") + " | quality-pass v0.3.2 fallback",
                            }
                        )
                    )
                    changed.append(
                        {
                            "id": q.id,
                            "action": "rewrite_temporal_fallback",
                            "article": art.num,
                            "after_a": answer,
                        }
                    )
                else:
                    out.append(q)
            else:
                out.append(replacement)
            continue

        out.append(q)

    # Final hygiene: ban boilerplate / ellipsis / remaniée / bad actors on civil/travail.
    hygiene_hits: list[str] = []
    for q in out:
        ans = q.reference_answer or ""
        if q.type in (QuestionType.MULTI_HOP, QuestionType.TEMPORAL):
            if "…" in ans or "Les deux textes se complètent" in ans:
                hygiene_hits.append(q.id)
            if "rédaction courante a été remaniée" in ans:
                hygiene_hits.append(q.id)
        if q.type == QuestionType.MULTI_HOP and q.id != "q26":
            topic = q.topic or ""
            if "civil" in topic or "travail" in topic:
                if "Un professionnel se prévaut" in q.question:
                    hygiene_hits.append(q.id)

    leaks = scan_unanswerables_against_corpus(out, corpus)
    gold_out = GoldSet(
        version="0.3.2",
        corpus_snapshot=corpus.snapshot_id,
        language="fr",
        validated=False,
        notes=(
            "Gold v0.3.2 — passe qualité : réponses mh synthétisées sans troncature, "
            "gabarits d'acteur par domaine, temporal avec diff concret, coquilles "
            "corrigées. validated=false."
        ),
        questions=out,
    )
    batch = select_review_batch(out, size=40, must_include=SAMPLE_TO_REVIEW_IDS)
    stats = {
        "mode": "quality_pass_v032",
        "corpus_snapshot": corpus.snapshot_id,
        "n_articles": len(corpus.articles),
        "n_crossrefs": len(corpus.crossrefs),
        "selected_total": len(out),
        "selected_by_type": dict(Counter(q.type.value for q in out)),
        "multi_hop_by_code": dict(
            Counter(
                (q.topic or "").split(":")[1]
                for q in out
                if q.type == QuestionType.MULTI_HOP
                and q.topic
                and q.topic.startswith("crossref:")
            )
        ),
        "temporal_by_code": dict(
            Counter(
                (q.topic or "").split(":")[1]
                for q in out
                if q.type == QuestionType.TEMPORAL
                and q.topic
                and q.topic.startswith("temporal:")
            )
        ),
        "review_batch_ids": [q.id for q in batch],
        "review_batch_by_type": dict(Counter(q.type.value for q in batch)),
        "review_batch_codes_mh_t": {
            q.id: (q.topic or "")
            for q in batch
            if q.type in (QuestionType.MULTI_HOP, QuestionType.TEMPORAL)
        },
        "changed_ids": sorted({c["id"] for c in changed}),
        "changed_detail": changed,
        "replaced_temporal": [
            c for c in changed if c["action"] == "replace_temporal"
        ],
        "hygiene_hits": sorted(set(hygiene_hits)),
        "unanswerable_leaks_remaining": [
            {"id": q.id, "article_id": aid, "score": round(s, 3)}
            for q, aid, s in leaks
        ],
        "crossrefs_removed_prior": 1290,
    }

    if dry_run:
        return stats

    GOLD_PATH.write_text(
        json.dumps(gold_out.model_dump(mode="json"), ensure_ascii=False, indent=2)
        + "\n",
        encoding="utf-8",
    )
    STATS_PATH.write_text(
        json.dumps(stats, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    note = (
        "> **Correctifs revue (v0.3.2)** : réponses mh synthétisées (sans « … » ni "
        "passe-partout) ; gabarits d'acteur civil/travail/conso ; temporal avec "
        "diff concret (remplacement des items cosmétiques / tableaux DOM) ; "
        "coquilles corrigées."
    )
    write_review_batch(REVIEW_PATH, batch, corpus.articles, header_note=note)
    return stats


def main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument(
        "--quality-pass",
        action="store_true",
        help="Second-pass quality rewrite (v0.3.2) keeping IDs stable",
    )
    args = parser.parse_args(argv)
    if args.quality_pass:
        stats = run_quality_pass(dry_run=args.dry_run)
    else:
        stats = run_fixes(dry_run=args.dry_run)
    print("selected", stats["selected_total"], stats.get("selected_by_type"))
    print("mh codes", stats.get("multi_hop_by_code"))
    print("t codes", stats.get("temporal_by_code"))
    if "changed_ids" in stats:
        print("changed", len(stats["changed_ids"]), stats["changed_ids"][:25], "...")
    if "replaced_temporal" in stats:
        print(
            "replaced temporal",
            [
                (c["id"], c["from_article"], "→", c["to_article"])
                for c in stats["replaced_temporal"]
            ],
        )
    if "hygiene_hits" in stats:
        print("hygiene_hits", stats["hygiene_hits"])
    print("leaks remaining", stats.get("unanswerable_leaks_remaining"))
    print("batch mh/t topics", stats.get("review_batch_codes_mh_t"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

