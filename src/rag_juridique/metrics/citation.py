from __future__ import annotations

from dataclasses import dataclass


def _norm(num: str) -> str:
    return " ".join(num.replace(".", ". ").split()).upper()


@dataclass(frozen=True)
class CitationAccuracyResult:
    score: float
    n_cited: int
    n_supported: int
    abstained: bool


def citation_accuracy(
    cited_article_nums: list[str],
    retrieved_article_nums: list[str],
    *,
    abstained: bool = False,
) -> CitationAccuracyResult:
    """Precision of cited article numbers against the retrieved context.

    Abstentions score 1.0 (no unsupported citation claimed).
    Empty citations on a non-abstaining answer score 0.0.
    """
    if abstained:
        return CitationAccuracyResult(
            score=1.0, n_cited=0, n_supported=0, abstained=True
        )
    if not cited_article_nums:
        return CitationAccuracyResult(
            score=0.0, n_cited=0, n_supported=0, abstained=False
        )
    retrieved = {_norm(n) for n in retrieved_article_nums}
    supported = sum(1 for n in cited_article_nums if _norm(n) in retrieved)
    return CitationAccuracyResult(
        score=supported / len(cited_article_nums),
        n_cited=len(cited_article_nums),
        n_supported=supported,
        abstained=False,
    )


def mean_citation_accuracy(scores: list[float]) -> float:
    if not scores:
        return 0.0
    return sum(scores) / len(scores)
