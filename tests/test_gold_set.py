"""Validate committed data/gold/questions.json against frozen contracts."""

from __future__ import annotations

from collections import Counter
from pathlib import Path

from rag_juridique.contracts.gold import QuestionType
from rag_juridique.corpus.loader import load_corpus
from rag_juridique.gold.loader import load_gold_set

ROOT = Path(__file__).resolve().parents[1]
GOLD_PATH = ROOT / "data" / "gold" / "questions.json"
REVIEW_PATH = ROOT / "data" / "gold" / "REVIEW_BATCH_40.md"
STATS_PATH = ROOT / "data" / "gold" / "filter_stats.json"


def test_committed_gold_set_phase2_shape():
    gold = load_gold_set(GOLD_PATH)
    n = len(gold.questions)
    assert 150 <= n <= 200, f"expected 150–200 questions, got {n}"
    assert gold.validated is False
    assert all(q.validated is False for q in gold.questions)

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


def test_review_batch_and_stats_artifacts_exist():
    assert REVIEW_PATH.is_file()
    text = REVIEW_PATH.read_text(encoding="utf-8")
    assert "q08" in text
    assert "u01" in text
    assert "apparent_contradiction" in text or "`apparent_contradiction`" in text
    assert STATS_PATH.is_file()
