"""Tests for review-batch blocking fixes (sentence split, CrossRef, u02, ac05)."""

from __future__ import annotations

from pathlib import Path

from rag_juridique.contracts.corpus import Article
from rag_juridique.contracts.gold import QuestionType
from rag_juridique.corpus.loader import load_corpus
from rag_juridique.corpus.refs import build_crossrefs, is_false_cross_code_ref
from rag_juridique.gold.loader import load_gold_set
from rag_juridique.gold.review_fixes import scan_unanswerables_against_corpus
from rag_juridique.gold.textutil import (
    contrast_versions,
    first_sentence,
    fix_proper_nouns,
    is_territorial_renvoi_table,
    split_sentences,
)

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
    assert "…" not in first
    parts = split_sentences(text)
    assert len(parts) >= 2


def test_contrast_versions_is_concrete():
    old = (
        "France compétences est une institution nationale publique. "
        "Elle verse des fonds aux opérateurs de compétences."
    )
    new = (
        "France compétences est une institution nationale publique. "
        "Elle verse des fonds aux opérateurs de compétences dans la limite "
        "d'un montant fixé par arrêté."
    )
    out = contrast_versions(old, new)
    assert "remaniée" not in out
    assert (
        "limite" in out.lower()
        or "ajoute" in out.lower()
        or "dispose" in out.lower()
        or "modifie" in out.lower()
    )


def test_territorial_table_detection():
    text = (
        "Sont applicables dans les îles Wallis et Futuna, sous réserve des "
        "adaptations prévues à l'article L. 771-3, les dispositions des articles "
        "mentionnés dans la colonne de gauche du tableau ci-après."
    )
    assert is_territorial_renvoi_table(text)


def test_france_competences_casing():
    assert "France compétences" in fix_proper_nouns("france compétences est une institution")


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
            assert "…" not in ans
            assert "Les deux textes se complètent" not in ans
            assert "il faut donc combiner" not in ans.lower()
            assert "rédaction courante a été remaniée" not in ans
            assert ".." not in ans
        if q.type == QuestionType.MULTI_HOP and q.id != "q26":
            topic = q.topic or ""
            if "civil" in topic or "travail" in topic:
                assert "Un professionnel se prévaut" not in q.question
            # Handwritten answers: complete, cite both gold nums, no mid-cut.
            if q.id.startswith("mh"):
                ans = q.reference_answer or ""
                assert len(ans) >= 180
                for num in q.expected_article_nums:
                    assert num in ans or num.replace("L. ", "L.") in ans or num in q.question

    # Named items from the quality / handwrite passes.
    assert "France compétences" in (by_id["t15"].reference_answer or "")
    assert "L. 6123-5" in by_id["t15"].expected_article_nums
    assert "remaniée" not in (by_id["t15"].reference_answer or "")
    assert "Wallis" not in by_id["t02"].question
    assert "tableau ci-après" not in (by_id["t02"].reference_answer or "").lower()
    assert "1006" in (by_id["mh15"].reference_answer or "")
    assert "notaire" in (by_id["mh15"].reference_answer or "").lower()
    assert "initiative-emploi" in (by_id["mh28"].reference_answer or "")
    assert "L. 5134-72" in (by_id["mh28"].reference_answer or "")
    assert "1° Les apprentis." not in (by_id["mh28"].reference_answer or "")

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

