"""Auto-filters for gold candidates: answerability, dedup, leakage."""

from __future__ import annotations

from collections import Counter
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Iterable

from rag_juridique.contracts.corpus import Article
from rag_juridique.contracts.gold import Question, QuestionType
from rag_juridique.gold.textutil import fold, jaccard, tokens


@dataclass
class FilterStats:
    candidates_in: int = 0
    kept: int = 0
    rejected_answerability: int = 0
    rejected_dedup: int = 0
    rejected_leakage: int = 0
    rejected_schema: int = 0
    rejected_by_type: Counter[str] = field(default_factory=Counter)
    kept_by_type: Counter[str] = field(default_factory=Counter)

    def as_dict(self) -> dict:
        return {
            "candidates_in": self.candidates_in,
            "kept": self.kept,
            "rejected_answerability": self.rejected_answerability,
            "rejected_dedup": self.rejected_dedup,
            "rejected_leakage": self.rejected_leakage,
            "rejected_schema": self.rejected_schema,
            "rejected_by_type": dict(self.rejected_by_type),
            "kept_by_type": dict(self.kept_by_type),
            "rejection_rate": (
                round(1.0 - (self.kept / self.candidates_in), 4)
                if self.candidates_in
                else 0.0
            ),
        }


def _article_map(articles: Iterable[Article]) -> dict[str, Article]:
    return {a.id: a for a in articles}


def validate_schema_rules(q: Question) -> str | None:
    """Return rejection reason or None if OK."""
    if not q.id or not q.question.strip():
        return "missing_id_or_question"
    if q.type == QuestionType.UNANSWERABLE or q.unanswerable:
        if q.expected_article_ids:
            return "unanswerable_with_gold_ids"
        if q.type != QuestionType.UNANSWERABLE:
            return "unanswerable_flag_type_mismatch"
        return None
    if not q.expected_article_ids:
        return "answerable_without_gold_ids"
    if q.type == QuestionType.TEMPORAL and q.as_of is None:
        return "temporal_without_as_of"
    if q.type != QuestionType.TEMPORAL and q.as_of is not None:
        # Allow as_of only on temporal for this gold set.
        return "as_of_on_non_temporal"
    if q.type == QuestionType.MULTI_HOP and len(q.expected_article_ids) < 2:
        return "multi_hop_needs_two_articles"
    if q.validated:
        return "must_remain_validated_false"
    return None


def check_answerability(
    q: Question,
    by_id: dict[str, Article],
    *,
    gold_text_resolver: Callable[[Question, Article], str] | None = None,
) -> str | None:
    """Answerable: gold ids exist and reference tokens overlap article text.
    Unanswerable: no strong lexical hit against the whole corpus.

    ``gold_text_resolver`` optionally supplies historical text for temporal
    questions (``Corpus.version_at``), so answerability is checked against the
    version in force at ``as_of`` rather than the tip only.
    """
    if q.type == QuestionType.UNANSWERABLE or q.unanswerable:
        q_tok = tokens(q.question)
        # Strong overlap with any article suggests the question may be answerable.
        for art in by_id.values():
            if jaccard(q_tok, tokens(art.text)) >= 0.22:
                return "unanswerable_leaks_into_corpus"
        return None

    texts: list[str] = []
    for aid in q.expected_article_ids:
        art = by_id.get(aid)
        if art is None:
            return f"unknown_article_id:{aid}"
        if gold_text_resolver is not None:
            texts.append(gold_text_resolver(q, art))
        else:
            texts.append(art.text)
    joined = " ".join(texts)
    # Reference answer (if any) should be supported by gold articles.
    if q.reference_answer:
        ref_tok = tokens(q.reference_answer)
        # Drop ultra-generic tokens
        ref_tok -= {"dans", "pour", "avec", "sans", "dont", "cette", "cette", "etre"}
        if ref_tok and jaccard(ref_tok, tokens(joined)) < 0.08:
            # Also accept if a few distinctive content words appear.
            hits = sum(1 for t in ref_tok if t in fold(joined))
            if hits < max(2, len(ref_tok) // 5):
                return "reference_not_supported_by_gold"
    # Question should share some topical signal with gold text (not pure noise).
    if jaccard(tokens(q.question), tokens(joined)) < 0.02:
        # Very short definitional questions may have low overlap; require ≥1 shared token.
        if not (tokens(q.question) & tokens(joined)):
            return "question_unrelated_to_gold"
    return None


def check_leakage(q: Question, by_id: dict[str, Article]) -> str | None:
    """Reject if the question copies a long verbatim span from a gold article."""
    if q.type == QuestionType.UNANSWERABLE or q.unanswerable:
        return None
    q_fold = fold(q.question)
    for aid in q.expected_article_ids:
        art = by_id.get(aid)
        if art is None:
            continue
        art_fold = fold(art.text)
        # Sliding windows of 12+ chars from the question that look like quotes.
        # More precise: reject if a 10-token span of the question appears in article.
        q_toks = list(tokens(q.question))
        if len(q_toks) >= 10:
            for i in range(len(q_toks) - 9):
                span = " ".join(q_toks[i : i + 10])
                if span in art_fold and len(span) > 40:
                    return "verbatim_span_leakage"
        # Also reject if question contains a 60+ char contiguous substring of article.
        for i in range(0, max(0, len(art_fold) - 60), 20):
            frag = art_fold[i : i + 60]
            if frag in q_fold:
                return "verbatim_char_leakage"
    return None


def make_version_text_resolver(corpus) -> Callable[[Question, Article], str]:
    """Resolve gold support text via ``Corpus.version_at`` for temporal questions."""

    def _resolve(q: Question, art: Article) -> str:
        if q.type == QuestionType.TEMPORAL and q.as_of is not None:
            ver = corpus.version_at(art.id, q.as_of)
            if ver is not None and ver.text.strip():
                return ver.text
        return art.text

    return _resolve


def filter_candidates(
    candidates: list[Question],
    articles: list[Article],
    *,
    dedup_threshold: float = 0.82,
    gold_text_resolver: Callable[[Question, Article], str] | None = None,
    existing_for_dedup: list[Question] | None = None,
) -> tuple[list[Question], FilterStats]:
    stats = FilterStats(candidates_in=len(candidates))
    by_id = _article_map(articles)
    kept: list[Question] = []
    kept_tok: list[set[str]] = []
    if existing_for_dedup:
        kept_tok.extend(tokens(q.question) for q in existing_for_dedup)

    for q in candidates:
        # Force validated=false contract for this pipeline.
        if q.validated:
            q = q.model_copy(update={"validated": False})

        reason = validate_schema_rules(q)
        if reason:
            stats.rejected_schema += 1
            stats.rejected_by_type[q.type.value] += 1
            continue

        reason = check_answerability(
            q, by_id, gold_text_resolver=gold_text_resolver
        )
        if reason:
            stats.rejected_answerability += 1
            stats.rejected_by_type[q.type.value] += 1
            continue

        reason = check_leakage(q, by_id)
        if reason:
            stats.rejected_leakage += 1
            stats.rejected_by_type[q.type.value] += 1
            continue

        q_tok = tokens(q.question)
        dup = False
        for prev in kept_tok:
            if jaccard(q_tok, prev) >= dedup_threshold:
                dup = True
                break
        if dup:
            stats.rejected_dedup += 1
            stats.rejected_by_type[q.type.value] += 1
            continue

        kept.append(q)
        kept_tok.append(q_tok)
        stats.kept += 1
        stats.kept_by_type[q.type.value] += 1

    return kept, stats
