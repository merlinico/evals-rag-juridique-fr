from __future__ import annotations

import math


def passage_recall_at_k(
    expected_article_ids: list[str],
    retrieved_article_ids: list[str],
    k: int,
) -> float:
    """Deterministic passage recall@k over article ids.

    Returns 1.0 if any expected gold article appears in the top-k retrieved
    article ids (deduplicated order preserved), else 0.0. For multi-label gold,
    returns the fraction of expected ids found in top-k.
    """
    if not expected_article_ids:
        return 0.0
    top = retrieved_article_ids[:k]
    top_set = set(top)
    hits = sum(1 for aid in expected_article_ids if aid in top_set)
    return hits / len(expected_article_ids)


def mean_recall_at_k(
    cases: list[tuple[list[str], list[str]]],
    k: int,
) -> float:
    if not cases:
        return 0.0
    return sum(passage_recall_at_k(exp, ret, k) for exp, ret in cases) / len(cases)


def reciprocal_rank(
    expected_article_ids: list[str],
    retrieved_article_ids: list[str],
) -> float:
    """MRR contribution for one query (1/rank of first relevant hit)."""
    if not expected_article_ids:
        return 0.0
    expected = set(expected_article_ids)
    for i, aid in enumerate(retrieved_article_ids, start=1):
        if aid in expected:
            return 1.0 / i
    return 0.0


def mean_reciprocal_rank(
    cases: list[tuple[list[str], list[str]]],
) -> float:
    if not cases:
        return 0.0
    return sum(reciprocal_rank(exp, ret) for exp, ret in cases) / len(cases)


def _dcg(relevances: list[float]) -> float:
    score = 0.0
    for i, rel in enumerate(relevances, start=1):
        score += rel / math.log2(i + 1)
    return score


def ndcg_at_k(
    expected_article_ids: list[str],
    retrieved_article_ids: list[str],
    k: int,
) -> float:
    """nDCG@k with binary relevance over gold article ids."""
    if not expected_article_ids or k <= 0:
        return 0.0
    expected = set(expected_article_ids)
    top = retrieved_article_ids[:k]
    gains = [1.0 if aid in expected else 0.0 for aid in top]
    dcg = _dcg(gains)
    ideal_hits = min(len(expected), k)
    ideal = _dcg([1.0] * ideal_hits)
    if ideal <= 0.0:
        return 0.0
    return dcg / ideal


def mean_ndcg_at_k(
    cases: list[tuple[list[str], list[str]]],
    k: int,
) -> float:
    if not cases:
        return 0.0
    return sum(ndcg_at_k(exp, ret, k) for exp, ret in cases) / len(cases)
