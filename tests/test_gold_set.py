"""Validate committed data/gold/questions.json against frozen contracts."""

from __future__ import annotations

import re
from collections import Counter
from pathlib import Path

from rag_juridique.contracts.gold import QuestionType
from rag_juridique.corpus.loader import load_corpus
from rag_juridique.gold.loader import load_gold_set

ROOT = Path(__file__).resolve().parents[1]
GOLD_PATH = ROOT / "data" / "gold" / "questions.json"
REVIEW_PATH = ROOT / "data" / "gold" / "REVIEW_BATCH_40.md"
STATS_PATH = ROOT / "data" / "gold" / "filter_stats.json"

VALIDATOR = "validé par Nicolas Merli, 2026-11-14"


def _batch_ids_from_review() -> list[str]:
    text = REVIEW_PATH.read_text(encoding="utf-8")
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
    return ids


def test_committed_gold_set_phase2_shape():
    gold = load_gold_set(GOLD_PATH)
    n = len(gold.questions)
    assert 150 <= n <= 200, f"expected 150–200 questions, got {n}"
    # Whole-set flag stays false until full review.
    assert gold.validated is False

    batch_ids = _batch_ids_from_review()
    assert len(batch_ids) == 40
    by_id = {q.id: q for q in gold.questions}
    for qid in batch_ids:
        assert by_id[qid].validated is True
    assert sum(1 for q in gold.questions if q.validated) == 40
    assert all(
        q.validated is False for q in gold.questions if q.id not in set(batch_ids)
    )

    counts = Counter(q.type for q in gold.questions)
    for t in QuestionType:
        assert counts[t] >= 1, f"missing type {t}"

    corpus_ids = {a.id for a in load_corpus().articles}
    for q in gold.questions:
        if q.type == QuestionType.UNANSWERABLE:
            assert q.unanswerable
            assert q.expected_article_ids == []
        else:
            assert q.expected_article_ids
            assert set(q.expected_article_ids) <= corpus_ids
        if q.type == QuestionType.TEMPORAL:
            assert q.as_of is not None
        if q.type == QuestionType.MULTI_HOP:
            assert len(q.expected_article_ids) >= 2


def test_review_batch_verdicts_marked_ok():
    assert REVIEW_PATH.is_file()
    text = REVIEW_PATH.read_text(encoding="utf-8")
    assert "q08" in text
    assert "u01" in text
    assert VALIDATOR in text
    # Index column filled with OK for each of the 40 rows.
    assert text.count("| OK |") == 40
    assert f"Verdict : ☑ OK — {VALIDATOR}" in text
    assert text.count(f"Verdict : ☑ OK — {VALIDATOR}") == 40
    assert "Verdict : ☐ OK" not in text
    assert STATS_PATH.is_file()
