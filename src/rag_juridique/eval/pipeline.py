from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import yaml

from rag_juridique.corpus.loader import load_corpus
from rag_juridique.generation.ollama import (
    OllamaGenerator,
    extract_citations,
    is_abstention,
    load_generation_fixture,
)
from rag_juridique.metrics.abstention import abstention_metrics
from rag_juridique.metrics.faithfulness import faithfulness_score
from rag_juridique.metrics.retrieval import mean_recall_at_k, passage_recall_at_k
from rag_juridique.retrieval.hybrid import HybridRetriever


@dataclass
class ConfigCaseResult:
    question_id: str
    unanswerable: bool
    recall_at_k: float
    retrieved_article_ids: list[str]
    faithfulness: float
    abstained: bool
    answer: str


@dataclass
class ConfigMetrics:
    name: str
    chunk_size: int
    recall_at_k: float
    faithfulness: float
    correct_abstention_rate: float
    false_abstention_rate: float
    n_questions: int
    cases: list[ConfigCaseResult]


def load_config(path: Path | str) -> dict[str, Any]:
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_gold(path: Path | str) -> list[dict[str, Any]]:
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    return list(raw["questions"])


def run_config(
    *,
    name: str,
    chunk_size: int,
    config: dict[str, Any],
    gold: list[dict[str, Any]],
    use_fixtures: bool,
    fixtures_path: Path | None,
    generate: bool,
    dense_model: Any | None = None,
) -> tuple[ConfigMetrics, list[dict[str, Any]]]:
    corpus = load_corpus(config["corpus_path"])
    retrieval_cfg = config["retrieval"]
    metrics_cfg = config["metrics"]
    k = int(metrics_cfg["recall_k"])

    retriever = HybridRetriever(
        articles=corpus.articles,
        chunk_size=chunk_size,
        overlap=int(retrieval_cfg.get("overlap", 100)),
        embedding_model=str(retrieval_cfg["embedding_model"]),
        rrf_k=int(retrieval_cfg.get("rrf_k", 60)),
        dense_model=dense_model,
    )

    fixture_by_id: dict[str, dict[str, Any]] = {}
    if use_fixtures and fixtures_path and fixtures_path.exists():
        for item in load_generation_fixture(str(fixtures_path)):
            fixture_by_id[item["question_id"]] = item

    generator = None
    if generate:
        gen_cfg = config["generation"]
        generator = OllamaGenerator(
            model=str(gen_cfg["model"]),
            base_url=str(gen_cfg.get("base_url", "http://127.0.0.1:11434")),
            temperature=float(gen_cfg.get("temperature", 0.0)),
        )

    cases: list[ConfigCaseResult] = []
    generations: list[dict[str, Any]] = []
    recall_pairs: list[tuple[list[str], list[str]]] = []
    faith_scores: list[float] = []
    unans_flags: list[bool] = []
    abstained_flags: list[bool] = []

    top_k = int(retrieval_cfg.get("top_k", 5))

    for q in gold:
        qid = q["id"]
        question = q["question"]
        expected_ids = list(q.get("expected_article_ids") or [])
        unanswerable = bool(q.get("unanswerable"))

        hits = retriever.retrieve(question, top_k=top_k)
        retrieved_ids: list[str] = []
        for h in hits:
            if h.chunk.article_id not in retrieved_ids:
                retrieved_ids.append(h.chunk.article_id)

        if unanswerable:
            recall = 1.0  # no gold passages; excluded from mean below
        else:
            recall = passage_recall_at_k(expected_ids, retrieved_ids, k=k)
            recall_pairs.append((expected_ids, retrieved_ids))

        if use_fixtures and qid in fixture_by_id:
            gen = fixture_by_id[qid]
            answer = str(gen["answer"])
            cited = list(gen.get("cited_article_nums") or extract_citations(answer))
            abstained = bool(gen.get("abstained", is_abstention(answer)))
        elif generate and generator is not None:
            result = generator.generate(qid, question, hits)
            answer = result.answer
            cited = result.cited_article_nums
            abstained = result.abstained
            generations.append(
                {
                    "question_id": qid,
                    "question": question,
                    "answer": answer,
                    "cited_article_nums": cited,
                    "retrieved_article_ids": retrieved_ids,
                    "retrieved_chunk_ids": [h.chunk.chunk_id for h in hits],
                    "model": result.model,
                    "abstained": abstained,
                    "chunk_size": chunk_size,
                }
            )
        else:
            # Deterministic heuristic fallback for offline smoke tests.
            answer, cited, abstained = _heuristic_answer(q, hits)

        context_text = "\n".join(h.chunk.text for h in hits)
        retrieved_nums = [h.chunk.article_num for h in hits]
        faith = faithfulness_score(
            answer=answer,
            cited_article_nums=cited,
            retrieved_article_nums=retrieved_nums,
            context_text=context_text,
            overlap_threshold=float(metrics_cfg.get("overlap_threshold", 0.25)),
        )
        # For answerable questions that abstain incorrectly, faithfulness of the
        # abstention is counted separately via abstention metrics; still record score.
        faith_scores.append(faith.score)
        unans_flags.append(unanswerable)
        abstained_flags.append(abstained)

        cases.append(
            ConfigCaseResult(
                question_id=qid,
                unanswerable=unanswerable,
                recall_at_k=recall if not unanswerable else float("nan"),
                retrieved_article_ids=retrieved_ids,
                faithfulness=faith.score,
                abstained=abstained,
                answer=answer,
            )
        )

    abs_m = abstention_metrics(unans_flags, abstained_flags)
    metrics = ConfigMetrics(
        name=name,
        chunk_size=chunk_size,
        recall_at_k=mean_recall_at_k(recall_pairs, k=k),
        faithfulness=(sum(faith_scores) / len(faith_scores)) if faith_scores else 0.0,
        correct_abstention_rate=abs_m.correct_abstention_rate,
        false_abstention_rate=abs_m.false_abstention_rate,
        n_questions=len(gold),
        cases=cases,
    )
    return metrics, generations


def _heuristic_answer(q: dict[str, Any], hits: list[Any]) -> tuple[str, list[str], bool]:
    if q.get("unanswerable"):
        return "je ne sais pas", [], True
    if not hits:
        return "je ne sais pas", [], True
    nums = []
    seen = set()
    for h in hits[:3]:
        n = h.chunk.article_num
        if n not in seen:
            seen.add(n)
            nums.append(n)
    expected = list(q.get("expected_article_nums") or [])
    cite = expected[0] if expected else nums[0]
    snippet = hits[0].chunk.text[:280].rsplit(" ", 1)[0]
    answer = (
        f"D'après l'article {cite}, {snippet}… "
        f"Citations : {cite}"
    )
    return answer, [cite], False


def metrics_to_dict(m: ConfigMetrics) -> dict[str, Any]:
    return {
        "name": m.name,
        "chunk_size": m.chunk_size,
        "recall_at_k": round(m.recall_at_k, 4),
        "faithfulness": round(m.faithfulness, 4),
        "correct_abstention_rate": round(m.correct_abstention_rate, 4),
        "false_abstention_rate": round(m.false_abstention_rate, 4),
        "n_questions": m.n_questions,
        "cases": [asdict(c) for c in m.cases],
    }


def compare_to_baseline(
    current: dict[str, Any],
    baseline: dict[str, Any],
    min_recall: float,
    min_faithfulness: float,
) -> list[str]:
    """Return list of failure messages (empty if OK)."""
    failures: list[str] = []
    for name, cur in current.items():
        base = baseline.get(name)
        if cur["recall_at_k"] < min_recall:
            failures.append(
                f"{name}: recall@k={cur['recall_at_k']:.3f} < min {min_recall:.3f}"
            )
        if cur["faithfulness"] < min_faithfulness:
            failures.append(
                f"{name}: faithfulness={cur['faithfulness']:.3f} < min {min_faithfulness:.3f}"
            )
        if base is not None:
            if cur["recall_at_k"] + 1e-9 < base["recall_at_k"] - 0.05:
                failures.append(
                    f"{name}: recall@k dropped vs baseline "
                    f"({cur['recall_at_k']:.3f} < {base['recall_at_k']:.3f} - 0.05)"
                )
            if cur["faithfulness"] + 1e-9 < base["faithfulness"] - 0.05:
                failures.append(
                    f"{name}: faithfulness dropped vs baseline "
                    f"({cur['faithfulness']:.3f} < {base['faithfulness']:.3f} - 0.05)"
                )
    return failures
