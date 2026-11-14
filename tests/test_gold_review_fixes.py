"""Tests for review-batch blocking fixes (sentence split, CrossRef, u02, ac05)."""

from __future__ import annotations

from pathlib import Path

from rag_juridique.contracts.corpus import Article, CrossRef, CrossRefKind
from rag_juridique.contracts.gold import QuestionType
from rag_juridique.corpus.refs import build_crossrefs, is_false_cross_code_ref
from rag_juridique.gold.loader import load_gold_set
from rag_juridique.gold.review_fixes import scan_unanswerables_against_corpus
from rag_juridique.gold.textutil import first_sentence, split_sentences
from rag_juridique.corpus.loader import load_corpus

ROOT = Path(__file__).resolve().parents[1]


def test_first_sentence_keeps_legal_abbreviations():
    text = (
        "La garantie mentionnée à l'article L. 112-5 prend fin : 1° A la date "
        "à laquelle la situation change. Une autre phrase."
    )
    first = first_sentence(text, max_chars=400)
    assert "L. 112-5" in first
    assert "L. L." not in first
    assert "1°" in first
    parts = split_sentences(text)
    assert len(parts) >= 2


def test_build_crossrefs_drops_foreign_code_qualifier():
    arts = [
        Article(
            id="src",
            num="L. 121-22",
            title="x",
            text=(
                "Interdit au titre de l'article L. 762-2 du code de commerce "
                "et de l'article L. 122-24 du présent code."
            ),
            code="consommation",
        ),
        Article(
            id="fake_conso",
            num="L. 762-2",
            title="y",
            text="Texte consommation suffisamment long pour être indexé correctement ici.",
            code="consommation",
        ),
        Article(
            id="ok",
            num="L. 122-24",
            title="z",
            text="Texte présent code également suffisamment long pour l'indexation.",
            code="consommation",
        ),
    ]
    refs = build_crossrefs(arts)
    targets = {r.target_article_id for r in refs}
    assert "fake_conso" not in targets
    assert "ok" in targets


def test_committed_gold_review_fixes():
    gold = load_gold_set(ROOT / "data" / "gold" / "questions.json")
    by_id = {q.id: q for q in gold.questions}

    u02 = by_id["u02"]
    assert u02.type == QuestionType.DIRECT
    assert "L. 3141-3" in u02.expected_article_nums
    assert u02.unanswerable is False

    ac05 = by_id["ac05"]
    assert "professionnels et les non-professionnels" in ac05.question
    assert "étend" in (ac05.reference_answer or "").lower()

    for q in gold.questions:
        if q.type in (QuestionType.MULTI_HOP, QuestionType.TEMPORAL):
            ans = q.reference_answer or ""
            assert "L. L." not in ans
            assert "Le renvoi (renvoi)" not in ans

    corpus = load_corpus()
    leaks = scan_unanswerables_against_corpus(list(gold.questions), corpus)
    assert leaks == []

    # False edge gone from graph
    src = corpus.by_num("consommation")["L. 121-22"]
    bad = [
        r
        for r in corpus.crossrefs_from(src.id)
        if r.target_num == "L. 762-2"
        and is_false_cross_code_ref(
            r,
            source_text=src.text,
            source_code=src.code,
            target_code=corpus.by_id()[r.target_article_id].code,
        )
    ]
    assert bad == []
