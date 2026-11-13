from rag_juridique.metrics.abstention import abstention_metrics
from rag_juridique.metrics.faithfulness import faithfulness_score
from rag_juridique.metrics.retrieval import passage_recall_at_k


def test_recall_at_k():
    assert passage_recall_at_k(["a", "b"], ["x", "a", "y"], k=2) == 0.5
    assert passage_recall_at_k(["a"], ["a", "b"], k=1) == 1.0
    assert passage_recall_at_k(["a"], ["b", "c"], k=2) == 0.0


def test_abstention_metrics():
    m = abstention_metrics(
        is_unanswerable=[True, True, False, False],
        abstained=[True, False, True, False],
    )
    assert m.correct_abstention_rate == 0.5
    assert m.false_abstention_rate == 0.5


def test_faithfulness_requires_supported_citation():
    ok = faithfulness_score(
        answer=(
            "Selon l'article L. 111-1, le professionnel communique au consommateur "
            "les informations essentielles. Citations : L. 111-1"
        ),
        cited_article_nums=["L. 111-1"],
        retrieved_article_nums=["L. 111-1", "L. 112-1"],
        context_text=(
            "le professionnel communique au consommateur les informations essentielles "
            "du bien ou du service"
        ),
        overlap_threshold=0.2,
    )
    assert ok.score == 1.0

    bad = faithfulness_score(
        answer="Réponse sans preuve",
        cited_article_nums=[],
        retrieved_article_nums=["L. 111-1"],
        context_text="contexte",
        overlap_threshold=0.2,
    )
    assert bad.score == 0.0


def test_abstention_is_faithful():
    r = faithfulness_score(
        answer="je ne sais pas",
        cited_article_nums=[],
        retrieved_article_nums=[],
        context_text="",
    )
    assert r.score == 1.0
    assert r.abstained
