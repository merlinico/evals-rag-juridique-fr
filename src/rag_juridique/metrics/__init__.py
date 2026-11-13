from rag_juridique.metrics.abstention import abstention_metrics, risk_coverage_curve
from rag_juridique.metrics.citation import citation_accuracy
from rag_juridique.metrics.errors import error_breakdown_by_type
from rag_juridique.metrics.faithfulness import faithfulness_score
from rag_juridique.metrics.retrieval import (
    mean_ndcg_at_k,
    mean_reciprocal_rank,
    ndcg_at_k,
    passage_recall_at_k,
    reciprocal_rank,
)
from rag_juridique.metrics.stats import bootstrap_ci, paired_regression_test

__all__ = [
    "abstention_metrics",
    "bootstrap_ci",
    "citation_accuracy",
    "error_breakdown_by_type",
    "faithfulness_score",
    "mean_ndcg_at_k",
    "mean_reciprocal_rank",
    "ndcg_at_k",
    "paired_regression_test",
    "passage_recall_at_k",
    "reciprocal_rank",
    "risk_coverage_curve",
]
