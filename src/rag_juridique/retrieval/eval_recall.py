"""Compute passage recall@k per retrieval config_id (agent c reporting helper)."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Sequence

from rag_juridique.contracts.corpus import Article, ArticleVersion, CrossRef, CrossRefKind
from rag_juridique.contracts.gold import Question
from rag_juridique.corpus.loader import (
    default_crossrefs_path,
    default_versions_path,
    load_corpus,
    load_crossrefs,
    load_versions,
)
from rag_juridique.gold.loader import load_gold
from rag_juridique.metrics.retrieval import mean_recall_at_k, passage_recall_at_k
from rag_juridique.retrieval.light import is_heavy_enabled
from rag_juridique.retrieval.registry import (
    all_config_ids,
    build_retriever,
    describe_config,
    light_config_ids,
)


def load_optional_versions(path: Path | str | None = None) -> list[ArticleVersion]:
    """Load ArticleVersion rows via corpus loader when the snapshot file exists."""
    candidate = Path(path) if path else default_versions_path()
    if not candidate.is_file():
        return []
    return load_versions(candidate)


def load_optional_cross_refs(path: Path | str | None = None) -> list[CrossRef]:
    """Load CrossRef edges via corpus loader when the snapshot file exists."""
    candidate = Path(path) if path else default_crossrefs_path()
    if not candidate.is_file():
        return []
    return load_crossrefs(candidate)


def recall_for_config(
    config_id: str,
    *,
    articles: list[Article],
    gold: list[Question],
    k: int = 5,
    versions: list[ArticleVersion] | None = None,
    cross_refs: Sequence[CrossRef] | None = None,
    dense_model: Any | None = None,
    rerank_model: Any | None = None,
) -> dict[str, Any]:
    """Run retrieval over answerable gold questions; return recall@k summary."""
    meta = describe_config(config_id)
    computable = True
    note = ""
    if meta.heavy and not is_heavy_enabled() and dense_model is None:
        # Still runnable via HashEncoder, but recall is not meaningful for bge-m3.
        computable = False
        note = "hash-encoder stand-in (set RAG_HEAVY=1 for real bge-m3 / reranker)"

    retriever = build_retriever(
        config_id,
        articles,
        versions=versions,
        cross_refs=cross_refs,
        dense_model=dense_model,
        rerank_model=rerank_model,
    )

    pairs: list[tuple[list[str], list[str]]] = []
    per_question: list[dict[str, Any]] = []
    for q in gold:
        if q.unanswerable:
            continue
        hits = retriever.retrieve(q.question, k=k, as_of=q.as_of)
        retrieved: list[str] = []
        for h in hits:
            if h.chunk.article_id not in retrieved:
                retrieved.append(h.chunk.article_id)
        expected = list(q.expected_article_ids)
        score = passage_recall_at_k(expected, retrieved, k=k)
        pairs.append((expected, retrieved))
        per_question.append(
            {
                "question_id": q.id,
                "recall_at_k": score,
                "retrieved_article_ids": retrieved,
            }
        )

    mean = mean_recall_at_k(pairs, k=k)
    return {
        "config_id": config_id,
        "retriever": meta.retriever_key,
        "chunker": meta.chunker_key,
        "heavy": meta.heavy,
        "computable": computable,
        "note": note,
        "k": k,
        "n_answerable": len(pairs),
        "recall_at_k": round(mean, 4) if pairs else None,
        "per_question": per_question,
    }


def evaluate_configs(
    config_ids: Sequence[str] | None = None,
    *,
    corpus_path: Path | str | None = None,
    gold_path: Path | str | None = None,
    k: int = 5,
    light_only: bool | None = None,
    dense_model: Any | None = None,
) -> list[dict[str, Any]]:
    """Evaluate multiple configs; default = light CI set unless RAG_HEAVY."""
    corpus = load_corpus(corpus_path)
    gold = load_gold(gold_path or "data/gold/questions.json")
    versions = load_optional_versions()
    cross_refs = load_optional_cross_refs()

    if config_ids is None:
        if light_only is None:
            light_only = not is_heavy_enabled()
        config_ids = light_config_ids() if light_only else all_config_ids()

    results: list[dict[str, Any]] = []
    for cid in config_ids:
        results.append(
            recall_for_config(
                cid,
                articles=corpus.articles,
                gold=gold,
                k=k,
                versions=versions or None,
                cross_refs=cross_refs or None,
                dense_model=dense_model,
            )
        )
    return results


def make_fixture_cross_refs(articles: list[Article]) -> list[CrossRef]:
    """Tiny synthetic graph for tests when agent (a) data is absent."""
    if len(articles) < 2:
        return []
    a0, a1 = articles[0], articles[1]
    return [
        CrossRef(
            source_article_id=a0.id,
            target_article_id=a1.id,
            kind=CrossRefKind.EXPLICIT_CITATION,
            target_num=a1.num,
        )
    ]


def summarize_recall_table(results: list[dict[str, Any]]) -> str:
    """Markdown table for PR reporting."""
    lines = [
        "| config_id | recall@5 | computable | note |",
        "|---|---:|:---:|---|",
    ]
    for row in results:
        recall = row["recall_at_k"]
        recall_s = f"{recall:.4f}" if recall is not None else "n/a"
        lines.append(
            f"| `{row['config_id']}` | {recall_s} | "
            f"{'yes' if row['computable'] else 'no'} | {row.get('note') or ''} |"
        )
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    """CLI: ``python -m rag_juridique.retrieval.eval_recall``."""
    import argparse

    parser = argparse.ArgumentParser(description="Passage recall@k per retrieval config_id")
    parser.add_argument("--k", type=int, default=5)
    parser.add_argument(
        "--all",
        action="store_true",
        help="Evaluate all config ids (heavy ones use HashEncoder unless RAG_HEAVY=1)",
    )
    parser.add_argument("--config-id", action="append", default=None)
    args = parser.parse_args(argv)
    results = evaluate_configs(
        args.config_id,
        k=args.k,
        light_only=not args.all and args.config_id is None,
    )
    print(summarize_recall_table(results))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
