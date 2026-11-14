"""Tests for CrossRef / version_at gold regeneration."""

from __future__ import annotations

from datetime import date
from pathlib import Path

from rag_juridique.contracts.gold import QuestionType
from rag_juridique.corpus.loader import load_corpus
from rag_juridique.gold.loader import load_gold_set
from rag_juridique.gold.regen_graph import (
    generate_multi_hop_from_corpus,
    generate_temporal_from_versions,
)

ROOT = Path(__file__).resolve().parents[1]


def test_multi_hop_from_real_crossrefs():
    corpus = load_corpus()
    qs = generate_multi_hop_from_corpus(corpus, target=12)
    assert len(qs) >= 10
    by_id = corpus.by_id()
    for q in qs:
        assert q.type == QuestionType.MULTI_HOP
        assert len(q.expected_article_ids) >= 2
        src, tgt = q.expected_article_ids[0], q.expected_article_ids[1]
        assert src in by_id and tgt in by_id
        # At least one directed CrossRef links the pair (either direction).
        forwards = {r.target_article_id for r in corpus.crossrefs_from(src)}
        backwards = {r.target_article_id for r in corpus.crossrefs_from(tgt)}
        assert tgt in forwards or src in backwards
        assert q.validated is False


def test_temporal_version_differs_from_tip():
    corpus = load_corpus()
    qs = generate_temporal_from_versions(corpus, target=10)
    assert len(qs) >= 8
    for q in qs:
        assert q.type == QuestionType.TEMPORAL
        assert q.as_of is not None
        aid = q.expected_article_ids[0]
        tip = corpus.by_id()[aid]
        ver = corpus.version_at(aid, q.as_of)
        assert ver is not None
        assert ver.text.strip() != tip.text.strip()
        assert q.validated is False


def test_committed_gold_after_regen_has_graph_backed_types():
    gold = load_gold_set(ROOT / "data" / "gold" / "questions.json")
    corpus = load_corpus()
    mh = [q for q in gold.questions if q.type == QuestionType.MULTI_HOP and q.id != "q26"]
    temporal = [q for q in gold.questions if q.type == QuestionType.TEMPORAL]
    assert len(mh) >= 35
    assert len(temporal) >= 28
    # Spot-check a few temporal diffs against the live corpus.
    for q in temporal[:5]:
        ver = corpus.version_at(q.expected_article_ids[0], q.as_of)  # type: ignore[arg-type]
        tip = corpus.by_id()[q.expected_article_ids[0]]
        assert ver is not None
        assert ver.text.strip() != tip.text.strip()
    assert gold.corpus_snapshot == corpus.snapshot_id or gold.version >= "0.3.0"
