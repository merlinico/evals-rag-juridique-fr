from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class AbstentionMetrics:
    correct_abstention_rate: float
    false_abstention_rate: float
    n_unanswerable: int
    n_answerable: int
    n_correct_abstentions: int
    n_false_abstentions: int


@dataclass(frozen=True)
class RiskCoveragePoint:
    coverage: float
    risk: float
    n_answered: int
    threshold: float


@dataclass(frozen=True)
class RiskCoverageCurve:
    points: list[RiskCoveragePoint]
    auc_risk: float
    risk_at_full_coverage: float

    def as_dict(self) -> dict:
        return {
            "auc_risk": self.auc_risk,
            "risk_at_full_coverage": self.risk_at_full_coverage,
            "points": [
                {
                    "coverage": p.coverage,
                    "risk": p.risk,
                    "n_answered": p.n_answered,
                    "threshold": p.threshold,
                }
                for p in self.points
            ],
        }


def abstention_metrics(
    is_unanswerable: list[bool],
    abstained: list[bool],
) -> AbstentionMetrics:
    if len(is_unanswerable) != len(abstained):
        raise ValueError("is_unanswerable and abstained must have same length")

    n_unans = sum(1 for u in is_unanswerable if u)
    n_ans = len(is_unanswerable) - n_unans
    correct = sum(1 for u, a in zip(is_unanswerable, abstained) if u and a)
    false_abs = sum(1 for u, a in zip(is_unanswerable, abstained) if (not u) and a)

    return AbstentionMetrics(
        correct_abstention_rate=(correct / n_unans) if n_unans else 0.0,
        false_abstention_rate=(false_abs / n_ans) if n_ans else 0.0,
        n_unanswerable=n_unans,
        n_answerable=n_ans,
        n_correct_abstentions=correct,
        n_false_abstentions=false_abs,
    )


def risk_coverage_curve(
    correct: list[bool],
    confidence: list[float],
) -> RiskCoverageCurve:
    """Selective-prediction risk-coverage curve.

    Items are answered in decreasing confidence order. At each prefix:
    - coverage = answered / N
    - risk = error rate among answered (1 - accuracy)

    Abstentions should be given low confidence so they are deferred first.
    """
    if len(correct) != len(confidence):
        raise ValueError("correct and confidence must have same length")
    n = len(correct)
    if n == 0:
        return RiskCoverageCurve(points=[], auc_risk=0.0, risk_at_full_coverage=0.0)

    order = sorted(range(n), key=lambda i: confidence[i], reverse=True)
    points: list[RiskCoveragePoint] = []
    errors = 0
    for rank, idx in enumerate(order, start=1):
        if not correct[idx]:
            errors += 1
        coverage = rank / n
        risk = errors / rank
        points.append(
            RiskCoveragePoint(
                coverage=coverage,
                risk=risk,
                n_answered=rank,
                threshold=float(confidence[idx]),
            )
        )

    # Trapezoidal AUC over coverage in [0, 1] (lower is better).
    auc = 0.0
    prev_cov = 0.0
    prev_risk = points[0].risk if points else 0.0
    for p in points:
        auc += (p.coverage - prev_cov) * (p.risk + prev_risk) / 2.0
        prev_cov = p.coverage
        prev_risk = p.risk
    return RiskCoverageCurve(
        points=points,
        auc_risk=auc,
        risk_at_full_coverage=points[-1].risk if points else 0.0,
    )


def abstention_confidence(
    abstained: bool,
    overlap: float,
    citation_supported: bool,
) -> float:
    """Heuristic confidence for risk-coverage when the model has no logits."""
    if abstained:
        return 0.0
    bonus = 0.25 if citation_supported else 0.0
    return min(1.0, max(0.0, float(overlap) + bonus))
