"""Tests for gold generation / filtering / review batch (agent b)."""

from __future__ import annotations

from datetime import date
from pathlib import Path

from rag_juridique.contracts.gold import GoldSet, Question, QuestionType
from rag_juridique.corpus.loader import load_corpus
from rag_juridique.gold.build import build_gold_set
from rag_juridique.gold.crossrefs import extract_edges_from_text, resolve_cross_refs
from rag_juridique.gold.filters import filter_candidates, validate_schema_rules
from rag_juridique.gold.generate import generate_candidates, migrate_mvp_questions
from rag_juridique.gold.loader import load_gold_set
from rag_juridique.gold.review import SAMPLE_TO_REVIEW_IDS, select_review_batch

ROOT = Path(__file__).resolve().parents[1]


def test_crossref_extraction_finds_in_corpus_targets():
    corpus = load_corpus()
    edges = extract_edges_from_text(corpus.articles)
    assert edges
    by_id = {a.id: a for a in corpus.articles}
    for e in edges:
        assert e.source_id in by_id
        assert e.target_id in by_id
        assert e.source_id != e.target_id


def test_resolve_cross_refs_falls_back_without_file(tmp_path: Path):
    corpus = load_corpus()
    missing = tmp_path / "nope.json"
    edges = resolve_cross_refs(corpus.articles, cross_refs_path=missing)
    assert len(edges) >= 10


def test_filter_rejects_unanswerable_with_ids():
    corpus = load_corpus()
    bad = Question(
        id="bad_u",
        question="Question hors corpus ?",
        type=QuestionType.UNANSWERABLE,
        expected_article_ids=[corpus.articles[0].id],
        unanswerable=True,
        validated=False,
    )
    assert validate_schema_rules(bad) == "unanswerable_with_gold_ids"
    kept, stats = filter_candidates([bad], corpus.articles)
    assert kept == []
    assert stats.rejected_schema == 1


def test_filter_candidates_forces_validated_false():
    q = Question(
        id="x",
        question="Quelle est la durée de rétractation pour un contrat à distance ?",
        type=QuestionType.DIRECT,
        expected_article_ids=["LEGIARTI000032226842"],
        expected_article_nums=["L. 221-18"],
        reference_answer="Le délai de rétractation est de quatorze jours.",
        validated=True,
    )
    # Committed gold may be validated=true; schema allows it.
    assert validate_schema_rules(q) is None
    # Generation filter still normalizes candidates to validated=false.
    arts = [
        a
        for a in load_corpus().articles
        if a.id == "LEGIARTI000032226842"
    ]
    kept, _stats = filter_candidates([q], arts)
    assert len(kept) == 1
    assert kept[0].validated is False


def test_migrate_mvp_infers_types():
    raw = [
        {
            "id": "q01",
            "question": "Test ?",
            "expected_article_ids": ["A"],
            "expected_article_nums": ["L. 1"],
            "unanswerable": False,
            "validated": False,
        },
        {
            "id": "u01",
            "question": "Hors ?",
            "expected_article_ids": [],
            "unanswerable": True,
            "validated": False,
        },
        {
            "id": "q26",
            "question": "Multi ?",
            "expected_article_ids": ["A", "B"],
            "expected_article_nums": ["L. 1", "L. 2"],
            "unanswerable": False,
            "validated": False,
        },
    ]
    qs = migrate_mvp_questions(raw)
    assert qs[0].type == QuestionType.DIRECT
    assert qs[1].type == QuestionType.UNANSWERABLE
    assert qs[2].type == QuestionType.MULTI_HOP


def test_generate_candidates_cover_five_types():
    corpus = load_corpus()
    mvp = load_gold_set(ROOT / "data" / "gold" / "questions.json")
    # Use only legacy-looking rows if file already expanded
    mvp_raw = [
        q.model_dump(mode="json")
        for q in mvp.questions
        if q.id.startswith(("q", "u")) and len(q.id) <= 4
    ]
    if len(mvp_raw) < 10:
        mvp_raw = [q.model_dump(mode="json") for q in mvp.questions[:35]]
    cands = generate_candidates(corpus.articles, mvp_raw=mvp_raw)
    types = {q.type for q in cands}
    assert types >= set(QuestionType)


def test_build_gold_set_size_and_types():
    gold, stats, batch = build_gold_set(target_min=150, target_max=200, review_size=40)
    assert isinstance(gold, GoldSet)
    assert 150 <= len(gold.questions) <= 200
    assert gold.validated is False
    assert all(not q.validated for q in gold.questions)
    by_type = stats["selected_by_type"]
    for t in QuestionType:
        assert by_type.get(t.value, 0) >= 1
    # Unanswerables have no gold ids
    for q in gold.questions:
        if q.type == QuestionType.UNANSWERABLE:
            assert q.expected_article_ids == []
            assert q.unanswerable
        if q.type == QuestionType.TEMPORAL:
            assert q.as_of is not None
        if q.type == QuestionType.MULTI_HOP:
            assert len(q.expected_article_ids) >= 2
    assert len(batch) == 40
    batch_ids = {q.id for q in batch}
    for qid in SAMPLE_TO_REVIEW_IDS:
        assert qid in batch_ids


def test_review_batch_stratified():
    gold, _, _ = build_gold_set(target_min=150, target_max=200)
    batch = select_review_batch(gold.questions, size=40)
    types = {q.type for q in batch}
    assert len(types) == 5


def test_temporal_question_roundtrip():
    q = Question(
        id="t_test",
        question="Au 2020-01-01, délai ?",
        type=QuestionType.TEMPORAL,
        expected_article_ids=["LEGIARTI000032226842"],
        as_of=date(2020, 1, 1),
        validated=False,
    )
    assert q.as_of == date(2020, 1, 1)
    dumped = q.model_dump(mode="json")
    assert dumped["as_of"] == "2020-01-01"
