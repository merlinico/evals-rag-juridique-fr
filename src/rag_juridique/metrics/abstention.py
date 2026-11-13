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
