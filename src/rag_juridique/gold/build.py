"""CLI: generate → filter → write gold set + review batch + stats.

Usage:
  uv run python -m rag_juridique.gold.build
  uv run python -m rag_juridique.gold.build --dry-run
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

from rag_juridique.contracts.gold import GoldSet
from rag_juridique.corpus.loader import load_corpus
from rag_juridique.gold.filters import filter_candidates
from rag_juridique.gold.generate import generate_candidates, select_balanced
from rag_juridique.gold.review import (
    SAMPLE_TO_REVIEW_IDS,
    select_review_batch,
    write_review_batch,
)

ROOT = Path(__file__).resolve().parents[3]
DEFAULT_GOLD = ROOT / "data" / "gold" / "questions.json"
DEFAULT_STATS = ROOT / "data" / "gold" / "filter_stats.json"
DEFAULT_REVIEW = ROOT / "data" / "gold" / "REVIEW_BATCH_40.md"
DEFAULT_CROSS_REFS = ROOT / "data" / "corpus" / "cross_refs.json"


def _load_mvp_raw(path: Path) -> list[dict]:
    if not path.is_file():
        return []
    raw = json.loads(path.read_text(encoding="utf-8"))
    return list(raw.get("questions") or [])


def build_gold_set(
    *,
    corpus_path: Path | None = None,
    existing_gold_path: Path = DEFAULT_GOLD,
    cross_refs_path: Path = DEFAULT_CROSS_REFS,
    target_min: int = 150,
    target_max: int = 200,
    review_size: int = 40,
) -> tuple[GoldSet, dict, list]:
    corpus = load_corpus(corpus_path)
    mvp_raw = _load_mvp_raw(existing_gold_path)
    # If existing file is already phase-2 sized, still re-run generation from MVP
    # rows that look like legacy (q01 / u01) to keep ids stable.
    if mvp_raw and len(mvp_raw) > 80:
        mvp_raw = [
            q
            for q in mvp_raw
            if str(q.get("id", "")).startswith(("q", "u"))
            and len(str(q.get("id", ""))) <= 4
        ]

    candidates = generate_candidates(
        corpus.articles,
        mvp_raw=mvp_raw or None,
        cross_refs_path=cross_refs_path if cross_refs_path.is_file() else cross_refs_path,
    )
    filtered, stats = filter_candidates(candidates, corpus.articles)
    selected = select_balanced(
        filtered,
        target_min=target_min,
        target_max=target_max,
    )

    snapshot = corpus.snapshot_id
    gold = GoldSet(
        version="0.2.0",
        corpus_snapshot=snapshot,
        language="fr",
        validated=False,
        notes=(
            "Gold set phase 2 (150–200). Généré par pipeline scripté "
            "(generate → auto-filter). validated=false jusqu'à revue humaine. "
            "Étendable : cross_refs.json / versions LEGI de l'agent corpus (a)."
        ),
        questions=selected,
    )
    batch = select_review_batch(
        selected,
        size=review_size,
        must_include=SAMPLE_TO_REVIEW_IDS,
    )
    payload_stats = stats.as_dict()
    payload_stats["selected_total"] = len(selected)
    payload_stats["selected_by_type"] = dict(
        Counter(q.type.value for q in selected)
    )
    payload_stats["review_batch_ids"] = [q.id for q in batch]
    payload_stats["review_batch_by_type"] = dict(
        Counter(q.type.value for q in batch)
    )
    payload_stats["corpus_snapshot"] = snapshot
    payload_stats["n_articles"] = len(corpus.articles)
    payload_stats["cross_refs_file_present"] = cross_refs_path.is_file()
    return gold, payload_stats, batch


def write_outputs(
    gold: GoldSet,
    stats: dict,
    batch: list,
    articles,
    *,
    gold_path: Path = DEFAULT_GOLD,
    stats_path: Path = DEFAULT_STATS,
    review_path: Path = DEFAULT_REVIEW,
) -> None:
    gold_path.parent.mkdir(parents=True, exist_ok=True)
    # Stable JSON: dump via pydantic then json for ensure_ascii
    data = gold.model_dump(mode="json")
    gold_path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    stats_path.write_text(
        json.dumps(stats, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    write_review_batch(review_path, batch, articles)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build phase-2 gold set")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--target-min", type=int, default=150)
    parser.add_argument("--target-max", type=int, default=200)
    parser.add_argument("--review-size", type=int, default=40)
    args = parser.parse_args(argv)

    gold, stats, batch = build_gold_set(
        target_min=args.target_min,
        target_max=args.target_max,
        review_size=args.review_size,
    )
    print("candidates_in:", stats["candidates_in"])
    print("kept_after_filter:", stats["kept"])
    print("selected:", stats["selected_total"], stats["selected_by_type"])
    print("rejected:", {
        k: stats[k]
        for k in (
            "rejected_answerability",
            "rejected_dedup",
            "rejected_leakage",
            "rejected_schema",
        )
    })
    print("review_batch:", len(batch), stats["review_batch_by_type"])

    if args.dry_run:
        return 0

    corpus = load_corpus()
    write_outputs(gold, stats, batch, corpus.articles)
    print(f"Wrote {DEFAULT_GOLD}")
    print(f"Wrote {DEFAULT_STATS}")
    print(f"Wrote {DEFAULT_REVIEW}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
