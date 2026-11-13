from rag_juridique.metrics.abstention import (
    abstention_metrics,
    risk_coverage_curve,
)
from rag_juridique.metrics.citation import citation_accuracy
from rag_juridique.metrics.errors import error_breakdown_by_type
from rag_juridique.metrics.faithfulness import faithfulness_score, split_claims
from rag_juridique.metrics.retrieval import (
    ndcg_at_k,
    passage_recall_at_k,
    reciprocal_rank,
)
from rag_juridique.metrics.stats import (
    bootstrap_ci,
    paired_regression_test,
)


def test_recall_at_k():
    assert passage_recall_at_k(["a", "b"], ["x", "a", "y"], k=2) == 0.5
    assert passage_recall_at_k(["a"], ["a", "b"], k=1) == 1.0
    assert passage_recall_at_k(["a"], ["b", "c"], k=2) == 0.0


def test_mrr_and_ndcg():
    assert reciprocal_rank(["a"], ["x", "a", "y"]) == 0.5
    assert reciprocal_rank(["a"], ["a", "b"]) == 1.0
    assert reciprocal_rank(["a"], ["b", "c"]) == 0.0
    # Ideal ranking of one relevant doc at rank 1 ⇒ nDCG=1
    assert ndcg_at_k(["a"], ["a", "b", "c"], k=3) == 1.0
    # Relevant at rank 2 is worse than ideal
    assert 0.0 < ndcg_at_k(["a"], ["x", "a", "y"], k=3) < 1.0
    assert ndcg_at_k(["a"], ["x", "y", "z"], k=3) == 0.0


def test_citation_accuracy():
    ok = citation_accuracy(["L. 111-1"], ["L. 111-1", "L. 112-1"])
    assert ok.score == 1.0
    partial = citation_accuracy(["L. 111-1", "L. 999-1"], ["L. 111-1"])
    assert partial.score == 0.5
    abst = citation_accuracy([], [], abstained=True)
    assert abst.score == 1.0


def test_abstention_metrics():
    m = abstention_metrics(
        is_unanswerable=[True, True, False, False],
        abstained=[True, False, True, False],
    )
    assert m.correct_abstention_rate == 0.5
    assert m.false_abstention_rate == 0.5


def test_risk_coverage_curve_monotone_coverage():
    curve = risk_coverage_curve(
        correct=[True, False, True, False],
        confidence=[0.9, 0.8, 0.2, 0.1],
    )
    coverages = [p.coverage for p in curve.points]
    assert coverages == sorted(coverages)
    assert curve.points[0].coverage == 0.25
    assert abs(curve.points[-1].coverage - 1.0) < 1e-9
    assert 0.0 <= curve.auc_risk <= 1.0


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
    assert ok.method == "overlap"

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


def test_split_claims_skips_citation_line():
    claims = split_claims(
        "Le délai est de 14 jours. Citations : L. 221-18, L. 221-19"
    )
    assert len(claims) == 1
    assert "14 jours" in claims[0]


def test_bootstrap_ci_contains_mean():
    values = [0.0, 1.0, 1.0, 0.0, 1.0]
    ci = bootstrap_ci(values, n_boot=200, seed=0)
    assert ci.ci_low <= ci.mean <= ci.ci_high
    assert ci.n == 5


def test_paired_regression_detects_drop():
    baseline = [1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0]
    current = [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
    result = paired_regression_test(
        current, baseline, metric="recall_at_k", alpha=0.05, n_boot=500, seed=1
    )
    assert result.mean_delta < 0
    assert result.significant is True


def test_paired_regression_no_false_alarm_on_identical():
    values = [1.0, 0.0, 1.0, 1.0, 0.0, 1.0]
    result = paired_regression_test(
        values, values, metric="faithfulness", alpha=0.05, n_boot=500, seed=2
    )
    assert result.mean_delta == 0.0
    assert result.significant is False


def test_error_breakdown_by_type():
    cases = [
        {
            "question_type": "direct",
            "unanswerable": False,
            "abstained": False,
            "recall_at_k": 1.0,
            "faithfulness": 1.0,
            "citation_accuracy": 1.0,
        },
        {
            "question_type": "direct",
            "unanswerable": False,
            "abstained": True,
            "recall_at_k": 0.0,
            "faithfulness": 1.0,
            "citation_accuracy": 1.0,
        },
        {
            "question_type": "unanswerable",
            "unanswerable": True,
            "abstained": True,
            "recall_at_k": None,
            "faithfulness": 1.0,
            "citation_accuracy": 1.0,
        },
    ]
    stats = error_breakdown_by_type(cases)
    assert stats["direct"].n == 2
    assert stats["direct"].false_abstentions == 1
    assert stats["direct"].missed_retrieval == 1
    assert stats["unanswerable"].n_errors == 0
