from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from rag_juridique.generation.ollama import is_abstention

_TOKEN_RE = re.compile(r"[\w\-']+", re.UNICODE)
_SENTENCE_RE = re.compile(r"(?<=[.!?…])\s+|\n+")

# Lazy singleton for optional NLI path (heavy; not loaded in CI by default).
_NLI_PIPELINE: Any | None = None
_NLI_MODEL_NAME: str | None = None


@dataclass(frozen=True)
class FaithfulnessResult:
    score: float
    has_citation: bool
    citation_supported: bool
    overlap: float
    abstained: bool
    method: str = "overlap"
    n_claims: int = 0
    n_supported_claims: int = 0
    claim_scores: tuple[float, ...] = ()


def _tokens(text: str) -> set[str]:
    return {t.lower() for t in _TOKEN_RE.findall(text) if len(t) > 2}


def token_overlap(answer: str, context: str) -> float:
    a = _tokens(answer)
    c = _tokens(context)
    if not a:
        return 0.0
    return len(a & c) / len(a)


def split_claims(answer: str) -> list[str]:
    """Split an answer into claim-like sentences (French punctuation aware)."""
    text = " ".join(answer.strip().split())
    if not text:
        return []
    # Drop trailing "Citations : …" block before sentence splitting so
    # article dots (L. 221-18) do not create phantom claims.
    text = re.sub(
        r"(?i)\bcitations\s*:.*$",
        "",
        text,
    ).strip()
    if not text or text.lower() == "je ne sais pas":
        return []
    # Protect article refs like "L. 111-1" from being split on the dot.
    protected = re.sub(
        r"\b([LRD])\.\s*(\d)",
        r"\1<#ART#>\2",
        text,
        flags=re.IGNORECASE,
    )
    parts = [p.strip() for p in _SENTENCE_RE.split(protected) if p.strip()]
    claims: list[str] = []
    for part in parts:
        restored = part.replace("<#ART#>", ". ")
        lower = restored.lower()
        if lower == "je ne sais pas":
            continue
        if re.fullmatch(r"([lrd]\.?\s*\d[\d\-.\s,]*)+", lower):
            continue
        claims.append(restored)
    return claims


def _norm(num: str) -> str:
    return " ".join(num.replace(".", ". ").split()).upper()


def _load_nli(model_name: str) -> Any:
    global _NLI_PIPELINE, _NLI_MODEL_NAME
    if _NLI_PIPELINE is not None and _NLI_MODEL_NAME == model_name:
        return _NLI_PIPELINE
    try:
        from transformers import pipeline
    except ImportError as exc:  # pragma: no cover - optional path
        raise RuntimeError(
            "NLI faithfulness requires the optional [nli] extra "
            "(transformers + torch). Install with: uv sync --extra nli"
        ) from exc
    _NLI_PIPELINE = pipeline(
        "text-classification",
        model=model_name,
        truncation=True,
        top_k=None,
    )
    _NLI_MODEL_NAME = model_name
    return _NLI_PIPELINE


def _entailment_score(nli: Any, premise: str, hypothesis: str) -> float:
    """Return P(entailment) for premise=context, hypothesis=claim."""
    # Many XNLI models expect premise/hypothesis pairs via text-pair inputs.
    outputs = nli({"text": premise, "text_pair": hypothesis})
    if isinstance(outputs, list) and outputs and isinstance(outputs[0], list):
        outputs = outputs[0]
    scores = {str(item["label"]).lower(): float(item["score"]) for item in outputs}
    for key, value in scores.items():
        if "entail" in key:
            return value
    # Fallback label ids used by some CamemBERT NLI checkpoints.
    if "label_2" in scores:
        return scores["label_2"]
    return scores.get("entailment", 0.0)


def claim_faithfulness_nli(
    answer: str,
    context_text: str,
    *,
    model_name: str,
    entailment_threshold: float = 0.5,
) -> tuple[float, list[float]]:
    """Claim-level faithfulness via local French/multilingual NLI.

    Each non-citation sentence is a claim; score = fraction with
    P(entailment | context, claim) >= threshold.
    """
    claims = split_claims(answer)
    if not claims:
        return 1.0, []
    if not context_text.strip():
        return 0.0, [0.0] * len(claims)
    nli = _load_nli(model_name)
    claim_scores: list[float] = []
    for claim in claims:
        p_entail = _entailment_score(nli, context_text, claim)
        claim_scores.append(1.0 if p_entail >= entailment_threshold else 0.0)
    return sum(claim_scores) / len(claim_scores), claim_scores


def faithfulness_score(
    answer: str,
    cited_article_nums: list[str],
    retrieved_article_nums: list[str],
    context_text: str,
    overlap_threshold: float = 0.25,
    *,
    use_nli: bool = False,
    nli_model: str | None = None,
    nli_entailment_threshold: float = 0.5,
) -> FaithfulnessResult:
    """Faithfulness without paid LLM-as-judge.

    CI-light default (overlap):
    1. Cite at least one article number, AND
    2. Every cited article appears in the retrieved context, AND
    3. Token overlap with the retrieved context exceeds `overlap_threshold`.

    Optional heavy path (`use_nli=True`): claim-level NLI entailment against
    context, still requiring supported citations. Overlap remains the fallback
    when NLI deps/model are unavailable.

    Abstentions score 1.0 (nothing claimed).
    """
    if is_abstention(answer):
        return FaithfulnessResult(
            score=1.0,
            has_citation=False,
            citation_supported=True,
            overlap=0.0,
            abstained=True,
            method="abstention",
        )

    has_citation = len(cited_article_nums) > 0
    retrieved_set = {_norm(n) for n in retrieved_article_nums}
    citation_supported = has_citation and all(
        _norm(n) in retrieved_set for n in cited_article_nums
    )
    overlap = token_overlap(answer, context_text)

    if use_nli and nli_model:
        try:
            claim_score, claim_scores = claim_faithfulness_nli(
                answer,
                context_text,
                model_name=nli_model,
                entailment_threshold=nli_entailment_threshold,
            )
            ok = citation_supported and claim_score >= 1.0 - 1e-12
            # Soft score: average of binary citation gate and claim support rate.
            soft = (1.0 if citation_supported else 0.0) * claim_score
            return FaithfulnessResult(
                score=1.0 if ok else soft,
                has_citation=has_citation,
                citation_supported=citation_supported,
                overlap=overlap,
                abstained=False,
                method="nli",
                n_claims=len(claim_scores),
                n_supported_claims=int(sum(claim_scores)),
                claim_scores=tuple(claim_scores),
            )
        except Exception:
            # Keep CI / machines without torch working.
            pass

    ok = has_citation and citation_supported and overlap >= overlap_threshold
    return FaithfulnessResult(
        score=1.0 if ok else 0.0,
        has_citation=has_citation,
        citation_supported=citation_supported,
        overlap=overlap,
        abstained=False,
        method="overlap",
    )
