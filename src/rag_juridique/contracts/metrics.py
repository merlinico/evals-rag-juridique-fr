"""Metric result and report contracts."""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class MetricName(str, Enum):
    """Canonical metric names for reports and CI gates."""

    RECALL_AT_K = "recall_at_k"
    NDCG = "ndcg"
    MRR = "mrr"
    CITATION_ACCURACY = "citation_accuracy"
    FAITHFULNESS = "faithfulness"
    CORRECT_ABSTENTION_RATE = "correct_abstention_rate"
    FALSE_ABSTENTION_RATE = "false_abstention_rate"
    RISK_COVERAGE = "risk_coverage"


class MetricResult(BaseModel):
    """One named metric value, optionally with uncertainty."""

    model_config = ConfigDict(extra="ignore")

    name: MetricName | str
    value: float
    k: int | None = None
    ci_low: float | None = Field(default=None, description="Bootstrap CI lower")
    ci_high: float | None = Field(default=None, description="Bootstrap CI upper")
    n: int | None = Field(default=None, description="Sample size")
    by_question_type: dict[str, float] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)


class PerConfigMetrics(BaseModel):
    """Aggregated metrics for one retrieval/generation config."""

    model_config = ConfigDict(extra="ignore")

    config_id: str
    chunk_size: int | None = None
    metrics: list[MetricResult] = Field(default_factory=list)
    # Flat aliases kept so MVP baseline_metrics.json / report stay readable
    recall_at_k: float | None = None
    faithfulness: float | None = None
    correct_abstention_rate: float | None = None
    false_abstention_rate: float | None = None
    n_questions: int | None = None
    cases: list[dict[str, Any]] = Field(default_factory=list)

    def metric_map(self) -> dict[str, float]:
        out: dict[str, float] = {}
        for m in self.metrics:
            key = m.name.value if isinstance(m.name, MetricName) else str(m.name)
            out[key] = m.value
        if self.recall_at_k is not None:
            out.setdefault(MetricName.RECALL_AT_K.value, self.recall_at_k)
        if self.faithfulness is not None:
            out.setdefault(MetricName.FAITHFULNESS.value, self.faithfulness)
        if self.correct_abstention_rate is not None:
            out.setdefault(
                MetricName.CORRECT_ABSTENTION_RATE.value, self.correct_abstention_rate
            )
        if self.false_abstention_rate is not None:
            out.setdefault(
                MetricName.FALSE_ABSTENTION_RATE.value, self.false_abstention_rate
            )
        return out


class MetricReport(BaseModel):
    """Full eval report exchanged with CI / significance tests."""

    model_config = ConfigDict(extra="ignore")

    report_id: str = "default"
    corpus_snapshot: str | None = None
    gold_version: str | None = None
    configs: list[PerConfigMetrics] = Field(default_factory=list)
    comparisons: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Pairwise significance / delta rows between configs",
    )
    notes: str | None = None
