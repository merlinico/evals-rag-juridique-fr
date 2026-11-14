"""Mark REVIEW_BATCH_40 questions as validated=true after human sign-off."""

from __future__ import annotations

import json
import re
from pathlib import Path

from rag_juridique.contracts.gold import GoldSet
from rag_juridique.corpus.loader import load_corpus
from rag_juridique.gold.loader import load_gold_set
from rag_juridique.gold.review import write_review_batch

ROOT = Path(__file__).resolve().parents[1]
GOLD_PATH = ROOT / "data" / "gold" / "questions.json"
REVIEW_PATH = ROOT / "data" / "gold" / "REVIEW_BATCH_40.md"
STATS_PATH = ROOT / "data" / "gold" / "filter_stats.json"
CARD_PATH = ROOT / "data" / "gold" / "DATASET_CARD.md"

VALIDATOR = "validé par Nicolas Merli, 2026-11-14"


def parse_batch_ids(review_path: Path) -> list[str]:
    text = review_path.read_text(encoding="utf-8")
    # Index table rows: | q08 | `direct` | ... |
    ids: list[str] = []
    in_index = False
    for line in text.splitlines():
        if line.strip() == "## Index":
            in_index = True
            continue
        if in_index and line.startswith("## "):
            break
        if not in_index:
            continue
        m = re.match(r"^\|\s*([A-Za-z0-9_]+)\s*\|", line)
        if not m:
            continue
        qid = m.group(1)
        if qid.lower() == "id":
            continue
        ids.append(qid)
    if len(ids) != 40:
        raise RuntimeError(f"expected 40 batch ids, got {len(ids)}: {ids}")
    return ids


def main() -> int:
    batch_ids = parse_batch_ids(REVIEW_PATH)
    batch_set = set(batch_ids)
    corpus = load_corpus()
    gold = load_gold_set(GOLD_PATH)
    by_id = {q.id: q for q in gold.questions}
    missing = sorted(batch_set - set(by_id))
    if missing:
        raise RuntimeError(f"batch ids missing from gold: {missing}")

    # Snapshot answers/articles to prove we don't mutate them.
    before = {
        qid: (
            by_id[qid].question,
            by_id[qid].reference_answer,
            tuple(by_id[qid].expected_article_ids),
            tuple(by_id[qid].expected_article_nums),
        )
        for qid in batch_ids
    }

    out = []
    for q in gold.questions:
        if q.id in batch_set:
            out.append(
                q.model_copy(
                    update={
                        "validated": True,
                        "notes": (
                            ((q.notes or "").rstrip() + " | ")
                            if q.notes
                            else ""
                        )
                        + VALIDATOR,
                    }
                )
            )
        else:
            # Explicitly keep false; do not touch content.
            out.append(q if q.validated is False else q.model_copy(update={"validated": False}))

    for qid in batch_ids:
        q = next(x for x in out if x.id == qid)
        assert q.validated is True
        assert (
            q.question,
            q.reference_answer,
            tuple(q.expected_article_ids),
            tuple(q.expected_article_nums),
        ) == before[qid]

    n_validated = sum(1 for q in out if q.validated)
    assert n_validated == 40
    assert sum(1 for q in out if not q.validated) == len(out) - 40

    gold_out = GoldSet(
        version="0.3.4",
        corpus_snapshot=gold.corpus_snapshot or corpus.snapshot_id,
        language=gold.language,
        # Set-level flag stays false until the whole gold is reviewed.
        validated=False,
        notes=(
            "Gold v0.3.4 — REVIEW_BATCH_40 (40 questions) validated=true "
            f"({VALIDATOR}). Autres questions validated=false."
        ),
        questions=out,
    )

    batch_qs = [next(q for q in out if q.id == qid) for qid in batch_ids]
    GOLD_PATH.write_text(
        json.dumps(gold_out.model_dump(mode="json"), ensure_ascii=False, indent=2)
        + "\n",
        encoding="utf-8",
    )

    note = (
        f"> **Validation humaine** : les 40 questions de ce batch sont "
        f"`validated: true` ({VALIDATOR})."
    )
    write_review_batch(
        REVIEW_PATH,
        batch_qs,
        corpus.articles,
        header_note=note,
        validator_note=VALIDATOR,
    )

    stats = {
        "mode": "validate_review_batch_v034",
        "corpus_snapshot": corpus.snapshot_id,
        "n_questions": len(out),
        "n_validated": n_validated,
        "validated_ids": batch_ids,
        "validator": VALIDATOR,
        "gold_set_validated": False,
        "unchanged_answers_and_articles": True,
    }
    STATS_PATH.write_text(
        json.dumps(stats, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    if CARD_PATH.exists():
        text = CARD_PATH.read_text(encoding="utf-8")
        text = text.replace("v0.3.3", "v0.3.4")
        text = text.replace(
            "toutes `validated: false`.",
            "dont **40** (`REVIEW_BATCH_40`) `validated: true` ; le reste `validated: false`.",
        )
        text = text.replace(
            "**non validées juridiquement** (`validated: false`).",
            f"**40 validées** ({VALIDATOR}) ; le reste `validated: false`.",
        )
        CARD_PATH.write_text(text, encoding="utf-8")

    print("validated", n_validated, "ids", batch_ids[:5], "...")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
