from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import Any, Iterable


@dataclass(frozen=True)
class TypeErrorStats:
    question_type: str
    n: int
    n_errors: int
    error_rate: float
    mean_recall: float | None
    mean_faithfulness: float | None
    mean_citation_accuracy: float | None
    false_abstentions: int
    missed_retrieval: int
    unsupported_citation: int


def _mean(values: list[float]) -> float | None:
    if not values:
        return None
    return sum(values) / len(values)


def error_breakdown_by_type(
    cases: Iterable[dict[str, Any]],
) -> dict[str, TypeErrorStats]:
    """Aggregate error modes by gold `question_type`.

    A case is an error if any of:
    - answerable with recall_at_k < 1 (missed retrieval), or
    - false abstention, or
    - faithfulness == 0 on a non-abstaining answer.
    """
    buckets: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for case in cases:
        qtype = str(case.get("question_type") or "unknown")
        buckets[qtype].append(case)

    out: dict[str, TypeErrorStats] = {}
    for qtype, rows in sorted(buckets.items()):
        recalls: list[float] = []
        faiths: list[float] = []
        citations: list[float] = []
        n_errors = 0
        false_abs = 0
        missed = 0
        unsupported = 0
        for row in rows:
            unanswerable = bool(row.get("unanswerable"))
            abstained = bool(row.get("abstained"))
            recall = row.get("recall_at_k")
            faith = float(row.get("faithfulness", 0.0))
            cite = float(row.get("citation_accuracy", 0.0))
            faiths.append(faith)
            citations.append(cite)
            if recall is not None and recall == recall:  # not NaN
                recalls.append(float(recall))

            is_error = False
            if (not unanswerable) and abstained:
                false_abs += 1
                is_error = True
            if (not unanswerable) and recall is not None and recall == recall and float(recall) < 1.0:
                missed += 1
                is_error = True
            if (not abstained) and faith < 0.5:
                unsupported += 1
                is_error = True
            if is_error:
                n_errors += 1

        out[qtype] = TypeErrorStats(
            question_type=qtype,
            n=len(rows),
            n_errors=n_errors,
            error_rate=(n_errors / len(rows)) if rows else 0.0,
            mean_recall=_mean(recalls),
            mean_faithfulness=_mean(faiths),
            mean_citation_accuracy=_mean(citations),
            false_abstentions=false_abs,
            missed_retrieval=missed,
            unsupported_citation=unsupported,
        )
    return out


def breakdown_as_dict(stats: dict[str, TypeErrorStats]) -> dict[str, dict[str, Any]]:
    return {
        key: {
            "n": s.n,
            "n_errors": s.n_errors,
            "error_rate": round(s.error_rate, 4),
            "mean_recall": None if s.mean_recall is None else round(s.mean_recall, 4),
            "mean_faithfulness": (
                None if s.mean_faithfulness is None else round(s.mean_faithfulness, 4)
            ),
            "mean_citation_accuracy": (
                None
                if s.mean_citation_accuracy is None
                else round(s.mean_citation_accuracy, 4)
            ),
            "false_abstentions": s.false_abstentions,
            "missed_retrieval": s.missed_retrieval,
            "unsupported_citation": s.unsupported_citation,
        }
        for key, s in stats.items()
    }
