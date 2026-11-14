"""CLI: regenerate multi_hop + temporal from full corpus graph.

Keeps direct / unanswerable / apparent_contradiction from the current gold set.
Usage:
  uv run python -m rag_juridique.gold.regen_cli
"""

from __future__ import annotations

import argparse
import json
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
    generate_multi_hop_from_corpus,
    generate_temporal_from_versions,
)
from rag_juridique.gold.review import (
    SAMPLE_TO_REVIEW_IDS,
    select_review_batch,
    write_review_batch,
)

ROOT = Path(__file__).resolve().parents[3]
DEFAULT_GOLD = ROOT / "data" / "gold" / "questions.json"
DEFAULT_STATS = ROOT / "data" / "gold" / "filter_stats.json"
DEFAULT_REVIEW = ROOT / "data" / "gold" / "REVIEW_BATCH_40.md"
KEEP_TYPES = {
    QuestionType.DIRECT,
    QuestionType.UNANSWERABLE,
    QuestionType.APPARENT_CONTRADICTION,
}


def _merge_keep_mvp_multihop(existing: list[Question]) -> list[Question]:
    """Keep non-graph types; drop previous multi_hop/temporal (except MVP q26)."""
    kept: list[Question] = []
    for q in existing:
        if q.type in KEEP_TYPES:
            kept.append(q)
        elif q.id == "q26" and q.type == QuestionType.MULTI_HOP:
            # Legacy MVP multi-article question — retain.
            kept.append(q)
    return kept


def regen_graph_questions(
    *,
    gold_path: Path = DEFAULT_GOLD,
    multi_hop_target: int = 40,
    temporal_target: int = 30,
    review_size: int = 40,
) -> tuple[GoldSet, dict, list[Question], dict]:
    corpus = load_corpus()
    existing = load_gold_set(gold_path)
    kept = _merge_keep_mvp_multihop(existing.questions)

    mh_raw = generate_multi_hop_from_corpus(corpus, target=multi_hop_target + 40)
    # Reserve one slot if q26 kept
    mh_slots = multi_hop_target - (1 if any(q.id == "q26" for q in kept) else 0)
    t_raw = generate_temporal_from_versions(corpus, target=temporal_target + 60)

    resolver = make_version_text_resolver(corpus)
    # Dedup against kept questions; answerability uses tip + version texts.
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

    # Prefer balanced codes already baked into generators; trim to targets.
    mh_final = mh_kept[:mh_slots]
    # Re-number mh01.. excluding q26
    mh_renum: list[Question] = []
    n = 1
    for q in mh_final:
        mh_renum.append(q.model_copy(update={"id": f"mh{n:02d}"}))
        n += 1
    t_renum = [
        q.model_copy(update={"id": f"t{i:02d}"})
        for i, q in enumerate(t_kept[:temporal_target], start=1)
    ]

    combined = kept + mh_renum + t_renum
    # Stable order: keep non-graph first as in file, then mh, then t
    gold = GoldSet(
        version="0.3.0",
        corpus_snapshot=corpus.snapshot_id,
        language="fr",
        validated=False,
        notes=(
            "Gold set phase 2 — multi_hop via CrossRef réels et temporal via "
            f"Corpus.version_at (snapshot {corpus.snapshot_id}). "
            "validated=false jusqu'à revue humaine."
        ),
        questions=combined,
    )

    prev_batch_ids = []
    if DEFAULT_STATS.is_file():
        try:
            prev_batch_ids = list(
                json.loads(DEFAULT_STATS.read_text(encoding="utf-8")).get(
                    "review_batch_ids"
                )
                or []
            )
        except json.JSONDecodeError:
            prev_batch_ids = []

    batch = select_review_batch(
        combined,
        size=review_size,
        must_include=SAMPLE_TO_REVIEW_IDS,
    )
    new_ids = [q.id for q in batch]
    changed = sorted(set(prev_batch_ids) - set(new_ids))
    added = sorted(set(new_ids) - set(prev_batch_ids))

    # Content changes for ids that remain in the batch (mh/t regenerated).
    old_by_id = {q.id: q for q in existing.questions}
    content_changed = []
    for q in batch:
        prev = old_by_id.get(q.id)
        if prev is None:
            continue
        if prev.question != q.question or prev.expected_article_ids != q.expected_article_ids:
            content_changed.append(q.id)

    stats = {
        "mode": "regen_graph",
        "corpus_snapshot": corpus.snapshot_id,
        "n_articles": len(corpus.articles),
        "n_crossrefs": len(corpus.crossrefs),
        "n_versions": len(corpus.versions),
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
        "review_batch_ids": new_ids,
        "review_batch_by_type": dict(Counter(q.type.value for q in batch)),
        "review_batch_ids_removed": changed,
        "review_batch_ids_added": added,
        "review_batch_content_changed": content_changed,
        "cross_refs_file_present": True,
    }
    return gold, stats, batch, {
        "removed_from_batch": changed,
        "added_to_batch": added,
        "content_changed_in_batch": content_changed,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Regenerate multi_hop/temporal from CrossRef + version_at"
    )
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--multi-hop", type=int, default=40)
    parser.add_argument("--temporal", type=int, default=30)
    args = parser.parse_args(argv)

    gold, stats, batch, delta = regen_graph_questions(
        multi_hop_target=args.multi_hop,
        temporal_target=args.temporal,
    )
    print("selected:", stats["selected_total"], stats["selected_by_type"])
    print("multi_hop by code:", stats["multi_hop_by_code"])
    print("temporal by code:", stats["temporal_by_code"])
    print(
        "filter:",
        {
            k: stats[k]
            for k in (
                "candidates_in",
                "kept",
                "rejected_answerability",
                "rejected_dedup",
                "rejected_leakage",
                "rejected_schema",
                "rejection_rate",
            )
        },
    )
    print("review batch delta:", delta)

    if args.dry_run:
        return 0

    corpus = load_corpus()
    DEFAULT_GOLD.write_text(
        json.dumps(gold.model_dump(mode="json"), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    DEFAULT_STATS.write_text(
        json.dumps(stats, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    write_review_batch(DEFAULT_REVIEW, batch, corpus.articles)
    print(f"Wrote {DEFAULT_GOLD}")
    print(f"Wrote {DEFAULT_STATS}")
    print(f"Wrote {DEFAULT_REVIEW}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
