from __future__ import annotations

import re
from dataclasses import dataclass

from rag_juridique.generation.ollama import is_abstention

_TOKEN_RE = re.compile(r"[\w\-']+", re.UNICODE)


@dataclass(frozen=True)
class FaithfulnessResult:
    score: float
    has_citation: bool
    citation_supported: bool
    overlap: float
    abstained: bool


def _tokens(text: str) -> set[str]:
    return {t.lower() for t in _TOKEN_RE.findall(text) if len(t) > 2}


def token_overlap(answer: str, context: str) -> float:
    a = _tokens(answer)
    c = _tokens(context)
    if not a:
        return 0.0
    return len(a & c) / len(a)


def faithfulness_score(
    answer: str,
    cited_article_nums: list[str],
    retrieved_article_nums: list[str],
    context_text: str,
    overlap_threshold: float = 0.25,
) -> FaithfulnessResult:
    """Faithfulness without LLM-as-judge.

    A non-abstaining answer is faithful if:
    1. It cites at least one article number, AND
    2. Every cited article appears in the retrieved context article nums, AND
    3. Token overlap with the retrieved context exceeds `overlap_threshold`.

    Abstentions score 1.0 (nothing claimed).
    """
    if is_abstention(answer):
        return FaithfulnessResult(
            score=1.0,
            has_citation=False,
            citation_supported=True,
            overlap=0.0,
            abstained=True,
        )

    has_citation = len(cited_article_nums) > 0
    retrieved_set = {_norm(n) for n in retrieved_article_nums}
    citation_supported = has_citation and all(
        _norm(n) in retrieved_set for n in cited_article_nums
    )
    overlap = token_overlap(answer, context_text)
    ok = has_citation and citation_supported and overlap >= overlap_threshold
    return FaithfulnessResult(
        score=1.0 if ok else 0.0,
        has_citation=has_citation,
        citation_supported=citation_supported,
        overlap=overlap,
        abstained=False,
    )


def _norm(num: str) -> str:
    return " ".join(num.replace(".", ". ").split()).upper()
