"""Corpus phase-2: multi-code snapshot, hierarchy, versions, cross-refs."""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

from rag_juridique.contracts.corpus import Article, ArticleVersion, CrossRef, CrossRefKind
from rag_juridique.corpus.hierarchy import normalize_article_num, parse_contexte
from rag_juridique.corpus.loader import load_corpus
from rag_juridique.corpus.refs import build_crossrefs, extract_reference_spans
from rag_juridique.corpus.versions import version_in_force
from rag_juridique.gold.loader import load_gold

ROOT = Path(__file__).resolve().parents[1]
MVP_IDS = {
    "LEGIARTI000044142438",  # L. 111-1
    "LEGIARTI000032227331",  # L. 112-1
    "LEGIARTI000032227301",  # L. 121-1
}


def test_load_corpus_multi_code_and_hierarchy():
    corpus = load_corpus()
    assert len(corpus) >= 1000
    stats = corpus.stats()
    for code in ("civil", "consommation", "travail"):
        assert stats["articles_by_code"].get(code, 0) > 100
    sample = next(a for a in corpus.articles if a.code == "consommation" and a.livre)
    assert sample.livre
    assert sample.texte_cid == "LEGITEXT000006069565"
    assert isinstance(sample, Article)


def test_mvp_legiarti_ids_stable():
    corpus = load_corpus()
    by_id = corpus.by_id()
    for article_id in MVP_IDS:
        assert article_id in by_id
        assert by_id[article_id].code == "consommation"
    gold = load_gold(ROOT / "data" / "gold" / "questions.json")
    expected = {eid for q in gold for eid in q.expected_article_ids}
    missing = expected - set(by_id)
    assert not missing, f"gold ids missing from corpus: {sorted(missing)}"


def test_hierarchy_parser():
    h = parse_contexte(
        "Partie législative > Livre Ier : X > Titre II : Y > "
        "Chapitre III : Z > Section 1 : S"
    )
    assert h.livre and h.livre.startswith("Livre")
    assert h.titre and h.titre.startswith("Titre")
    assert h.chapitre and h.chapitre.startswith("Chapitre")
    assert h.section and h.section.startswith("Section")
    assert normalize_article_num("L217-3") == "L. 217-3"
    assert normalize_article_num("L. 217-3") == "L. 217-3"
    assert normalize_article_num("1240") == "1240"


def test_crossref_parser_and_graph():
    spans = extract_reference_spans(
        "Dans les conditions prévues à l'article L. 217-3 et à l'article L. 217-4."
    )
    nums = {n for n, *_ in spans}
    assert "L. 217-3" in nums
    assert "L. 217-4" in nums
    assert any(k == CrossRefKind.RENVOI for *_, k in spans)

    corpus = load_corpus()
    assert len(corpus.crossrefs) > 100
    src = next(
        a
        for a in corpus.articles
        if a.id == "LEGIARTI000044142438"
    )
    refs = corpus.crossrefs_from(src.id)
    assert refs
    assert all(isinstance(r, CrossRef) for r in refs)


def test_version_at_date():
    versions = [
        ArticleVersion(
            version_id="v1",
            article_id="a1",
            num="L. 1",
            text="ancien",
            debut=date(2016, 1, 1),
            fin=date(2021, 10, 1),
        ),
        ArticleVersion(
            version_id="v2",
            article_id="a1",
            num="L. 1",
            text="nouveau",
            debut=date(2021, 10, 1),
            fin=None,
        ),
    ]
    assert version_in_force(versions, date(2020, 6, 1)).version_id == "v1"
    assert version_in_force(versions, date(2021, 10, 1)).version_id == "v2"
    assert version_in_force(versions, date(2015, 1, 1)) is None

    corpus = load_corpus()
    tip_id = "LEGIARTI000044142438"
    tip = corpus.version_at(tip_id, date(2024, 6, 1))
    assert tip is not None
    assert tip.article_id == tip_id
    assert tip.text


def test_build_crossrefs_unit():
    arts = [
        Article(
            id="a",
            num="L. 1",
            title="Article L. 1",
            text="Voir l'article L. 2.",
            code="consommation",
        ),
        Article(
            id="b",
            num="L. 2",
            title="Article L. 2",
            text="Texte.",
            code="consommation",
        ),
    ]
    refs = build_crossrefs(arts)
    assert len(refs) == 1
    assert refs[0].source_article_id == "a"
    assert refs[0].target_article_id == "b"
    assert refs[0].target_num == "L. 2"


def test_manifest_matches_loader():
    manifest = json.loads(
        (ROOT / "data" / "corpus" / "manifest.json").read_text(encoding="utf-8")
    )
    corpus = load_corpus()
    assert manifest["n_articles"] == len(corpus)
    assert manifest["n_crossrefs"] == len(corpus.crossrefs)
    assert manifest["n_versions"] == len(corpus.versions)
