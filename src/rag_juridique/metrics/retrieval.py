from __future__ import annotations


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
