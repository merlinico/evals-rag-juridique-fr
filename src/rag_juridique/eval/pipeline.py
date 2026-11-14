from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

import yaml

from rag_juridique.contracts.generation import GenerationRecord
from rag_juridique.contracts.gold import Question, QuestionType
from rag_juridique.contracts.metrics import (
    MetricName,
    MetricReport,
    MetricResult,
    PerConfigMetrics,
)
from rag_juridique.corpus.loader import load_corpus
from rag_juridique.generation.ollama import (
    OllamaGenerator,
    extract_citations,
    is_abstention,
    load_generation_records,
)
from rag_juridique.metrics.abstention import (
    abstention_confidence,
    abstention_metrics,
    risk_coverage_curve,
)
from rag_juridique.metrics.citation import citation_accuracy
from rag_juridique.metrics.errors import breakdown_as_dict, error_breakdown_by_type
from rag_juridique.metrics.faithfulness import faithfulness_score
from rag_juridique.metrics.retrieval import (
    mean_ndcg_at_k,
    mean_recall_at_k,
    mean_reciprocal_rank,
    ndcg_at_k,
    passage_recall_at_k,
    reciprocal_rank,
)
from rag_juridique.metrics.stats import (
    PairedTestResult,
    align_paired_scores,
    bootstrap_ci,
    paired_regression_test,
)
from rag_juridique.retrieval.hybrid import HybridRetriever


@dataclass
class ConfigCaseResult:
    question_id: str
    question_type: str
    unanswerable: bool
    recall_at_k: float
    ndcg_at_k: float
    mrr: float
    retrieved_article_ids: list[str]
    faithfulness: float
    citation_accuracy: float
    abstained: bool
    confidence: float
    answer: str
    faithfulness_method: str = "overlap"


@dataclass
class ConfigMetrics:
    name: str
    chunk_size: int
    recall_at_k: float
    ndcg: float
    mrr: float
    citation_accuracy: float
    faithfulness: float
    correct_abstention_rate: float
    false_abstention_rate: float
    risk_coverage_auc: float
    n_questions: int
    cases: list[ConfigCaseResult]
    metric_results: list[MetricResult] = field(default_factory=list)
    error_breakdown: dict[str, Any] = field(default_factory=dict)
    risk_coverage: dict[str, Any] = field(default_factory=dict)
    recall_k: int = 5

    def to_contract(self) -> PerConfigMetrics:
        """Map aggregates onto the frozen PerConfigMetrics contract."""
        return PerConfigMetrics(
            config_id=self.name,
            chunk_size=self.chunk_size,
            recall_at_k=self.recall_at_k,
            faithfulness=self.faithfulness,
            correct_abstention_rate=self.correct_abstention_rate,
            false_abstention_rate=self.false_abstention_rate,
            n_questions=self.n_questions,
            cases=[asdict(c) for c in self.cases],
            metrics=list(self.metric_results),
        )


def load_config(path: Path | str) -> dict[str, Any]:
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def _question_type(q: Question) -> str:
    if isinstance(q.type, QuestionType):
        return q.type.value
    return str(q.type or ("unanswerable" if q.unanswerable else "direct"))


def _by_type_mean(
    cases: list[ConfigCaseResult],
    attr: str,
    *,
    skip_unanswerable: bool = False,
) -> dict[str, float]:
    buckets: dict[str, list[float]] = {}
    for case in cases:
        if skip_unanswerable and case.unanswerable:
            continue
        value = getattr(case, attr)
        if value != value:  # NaN
            continue
        buckets.setdefault(case.question_type, []).append(float(value))
    return {
        qtype: sum(vals) / len(vals)
        for qtype, vals in sorted(buckets.items())
        if vals
    }


def _metric_result(
    name: MetricName,
    values: list[float],
    *,
    k: int | None = None,
    by_question_type: dict[str, float] | None = None,
    n_boot: int = 1000,
    alpha: float = 0.05,
    seed: int = 42,
    metadata: dict[str, Any] | None = None,
) -> MetricResult:
    ci = bootstrap_ci(values, n_boot=n_boot, alpha=alpha, seed=seed)
    return MetricResult(
        name=name,
        value=ci.mean,
        k=k,
        ci_low=ci.ci_low,
        ci_high=ci.ci_high,
        n=ci.n,
        by_question_type=by_question_type or {},
        metadata=metadata or {},
    )


def run_config(
    *,
    name: str,
    chunk_size: int,
    config: dict[str, Any],
    gold: list[Question],
    use_fixtures: bool,
    fixtures_path: Path | None,
    generate: bool,
    dense_model: Any | None = None,
) -> tuple[ConfigMetrics, list[dict[str, Any]]]:
    corpus = load_corpus(config["corpus_path"])
    retrieval_cfg = config["retrieval"]
    metrics_cfg = config["metrics"]
    k = int(metrics_cfg["recall_k"])
    n_boot = int(metrics_cfg.get("bootstrap_n", 1000))
    alpha = float(metrics_cfg.get("significance_alpha", 0.05))
    seed = int(metrics_cfg.get("bootstrap_seed", 42))
    use_nli = bool(metrics_cfg.get("nli_enabled", False))
    nli_model = metrics_cfg.get(
        "nli_model",
        "MoritzLaurer/mDeBERTa-v3-base-xnli-multilingual-nli-2mil7",
    )
    nli_threshold = float(metrics_cfg.get("nli_entailment_threshold", 0.5))

    retriever = HybridRetriever(
        articles=corpus.articles,
        chunk_size=chunk_size,
        overlap=int(retrieval_cfg.get("overlap", 100)),
        embedding_model=str(retrieval_cfg["embedding_model"]),
        rrf_k=int(retrieval_cfg.get("rrf_k", 60)),
        dense_model=dense_model,
    )

    fixture_by_id: dict[str, GenerationRecord] = {}
    if use_fixtures and fixtures_path and fixtures_path.exists():
        for item in load_generation_records(str(fixtures_path)):
            fixture_by_id[item.question_id] = item

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
    recall_values: list[float] = []
    ndcg_values: list[float] = []
    mrr_values: list[float] = []
    faith_scores: list[float] = []
    citation_scores: list[float] = []
    unans_flags: list[bool] = []
    abstained_flags: list[bool] = []
    correct_flags: list[bool] = []
    confidence_scores: list[float] = []

    top_k = int(retrieval_cfg.get("top_k", 5))

    for q in gold:
        qid = q.id
        question = q.question
        expected_ids = list(q.expected_article_ids)
        unanswerable = bool(q.unanswerable)
        qtype = _question_type(q)

        hits = retriever.retrieve(question, k=top_k, as_of=q.as_of)
        retrieved_ids: list[str] = []
        for h in hits:
            if h.chunk.article_id not in retrieved_ids:
                retrieved_ids.append(h.chunk.article_id)

        if unanswerable:
            recall = float("nan")
            ndcg = float("nan")
            mrr = float("nan")
        else:
            recall = passage_recall_at_k(expected_ids, retrieved_ids, k=k)
            ndcg = ndcg_at_k(expected_ids, retrieved_ids, k=k)
            mrr = reciprocal_rank(expected_ids, retrieved_ids)
            recall_pairs.append((expected_ids, retrieved_ids))
            recall_values.append(recall)
            ndcg_values.append(ndcg)
            mrr_values.append(mrr)

        if use_fixtures and qid in fixture_by_id:
            gen = fixture_by_id[qid]
            answer = gen.answer
            cited = list(gen.cited_ids or extract_citations(answer))
            abstained = bool(
                gen.abstained if gen.abstained is not None else is_abstention(answer)
            )
        elif generate and generator is not None:
            result = generator.generate(qid, question, hits)
            answer = result.answer
            cited = result.cited_article_nums
            abstained = result.abstained
            record = GenerationRecord(
                question_id=qid,
                config_id=name,
                model=result.model,
                prompt_hash="",
                answer=answer,
                cited_ids=cited,
                abstained=abstained,
                question=question,
                retrieved_article_ids=retrieved_ids,
                retrieved_chunk_ids=[h.chunk.chunk_id for h in hits],
                chunk_size=chunk_size,
            )
            payload = record.model_dump()
            payload["cited_article_nums"] = cited
            generations.append(payload)
        else:
            answer, cited, abstained = _heuristic_answer(q, hits)

        context_text = "\n".join(h.chunk.text for h in hits)
        retrieved_nums = [h.chunk.article_num for h in hits]
        faith = faithfulness_score(
            answer=answer,
            cited_article_nums=cited,
            retrieved_article_nums=retrieved_nums,
            context_text=context_text,
            overlap_threshold=float(metrics_cfg.get("overlap_threshold", 0.25)),
            use_nli=use_nli,
            nli_model=str(nli_model) if nli_model else None,
            nli_entailment_threshold=nli_threshold,
        )
        cite = citation_accuracy(
            cited_article_nums=cited,
            retrieved_article_nums=retrieved_nums,
            abstained=abstained,
        )
        conf = abstention_confidence(
            abstained=abstained,
            overlap=faith.overlap,
            citation_supported=faith.citation_supported,
        )
        # Correctness for risk-coverage: unanswerable→abstain; else recall hit + faithful.
        if unanswerable:
            is_correct = abstained
        else:
            is_correct = (recall >= 1.0) and (faith.score >= 0.5) and (not abstained)

        faith_scores.append(faith.score)
        citation_scores.append(cite.score)
        unans_flags.append(unanswerable)
        abstained_flags.append(abstained)
        correct_flags.append(is_correct)
        confidence_scores.append(conf)

        cases.append(
            ConfigCaseResult(
                question_id=qid,
                question_type=qtype,
                unanswerable=unanswerable,
                recall_at_k=recall,
                ndcg_at_k=ndcg,
                mrr=mrr,
                retrieved_article_ids=retrieved_ids,
                faithfulness=faith.score,
                citation_accuracy=cite.score,
                abstained=abstained,
                confidence=conf,
                answer=answer,
                faithfulness_method=faith.method,
            )
        )

    abs_m = abstention_metrics(unans_flags, abstained_flags)
    rc = risk_coverage_curve(correct_flags, confidence_scores)
    case_dicts = [asdict(c) for c in cases]
    breakdown = breakdown_as_dict(error_breakdown_by_type(case_dicts))

    metric_results = [
        _metric_result(
            MetricName.RECALL_AT_K,
            recall_values,
            k=k,
            by_question_type=_by_type_mean(cases, "recall_at_k", skip_unanswerable=True),
            n_boot=n_boot,
            alpha=alpha,
            seed=seed,
        ),
        _metric_result(
            MetricName.NDCG,
            ndcg_values,
            k=k,
            by_question_type=_by_type_mean(cases, "ndcg_at_k", skip_unanswerable=True),
            n_boot=n_boot,
            alpha=alpha,
            seed=seed + 1,
        ),
        _metric_result(
            MetricName.MRR,
            mrr_values,
            by_question_type=_by_type_mean(cases, "mrr", skip_unanswerable=True),
            n_boot=n_boot,
            alpha=alpha,
            seed=seed + 2,
        ),
        _metric_result(
            MetricName.CITATION_ACCURACY,
            citation_scores,
            by_question_type=_by_type_mean(cases, "citation_accuracy"),
            n_boot=n_boot,
            alpha=alpha,
            seed=seed + 3,
        ),
        _metric_result(
            MetricName.FAITHFULNESS,
            faith_scores,
            by_question_type=_by_type_mean(cases, "faithfulness"),
            n_boot=n_boot,
            alpha=alpha,
            seed=seed + 4,
            metadata={"method": "nli" if use_nli else "overlap"},
        ),
        _metric_result(
            MetricName.CORRECT_ABSTENTION_RATE,
            [1.0 if (u and a) else 0.0 for u, a in zip(unans_flags, abstained_flags) if u],
            n_boot=n_boot,
            alpha=alpha,
            seed=seed + 5,
        ),
        _metric_result(
            MetricName.FALSE_ABSTENTION_RATE,
            [1.0 if ((not u) and a) else 0.0 for u, a in zip(unans_flags, abstained_flags) if not u],
            n_boot=n_boot,
            alpha=alpha,
            seed=seed + 6,
        ),
        MetricResult(
            name=MetricName.RISK_COVERAGE,
            value=rc.auc_risk,
            n=len(cases),
            metadata=rc.as_dict(),
        ),
    ]

    metrics = ConfigMetrics(
        name=name,
        chunk_size=chunk_size,
        recall_at_k=mean_recall_at_k(recall_pairs, k=k),
        ndcg=mean_ndcg_at_k(recall_pairs, k=k),
        mrr=mean_reciprocal_rank(recall_pairs),
        citation_accuracy=(sum(citation_scores) / len(citation_scores))
        if citation_scores
        else 0.0,
        faithfulness=(sum(faith_scores) / len(faith_scores)) if faith_scores else 0.0,
        correct_abstention_rate=abs_m.correct_abstention_rate,
        false_abstention_rate=abs_m.false_abstention_rate,
        risk_coverage_auc=rc.auc_risk,
        n_questions=len(gold),
        cases=cases,
        metric_results=metric_results,
        error_breakdown=breakdown,
        risk_coverage=rc.as_dict(),
        recall_k=k,
    )
    return metrics, generations


def _heuristic_answer(q: Question, hits: list[Any]) -> tuple[str, list[str], bool]:
    if q.unanswerable:
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
    expected = list(q.expected_article_nums)
    cite = expected[0] if expected else nums[0]
    snippet = hits[0].chunk.text[:280].rsplit(" ", 1)[0]
    answer = f"D'après l'article {cite}, {snippet}… Citations : {cite}"
    return answer, [cite], False


def metrics_to_dict(m: ConfigMetrics) -> dict[str, Any]:
    return {
        "name": m.name,
        "chunk_size": m.chunk_size,
        "recall_at_k": round(m.recall_at_k, 4),
        "ndcg": round(m.ndcg, 4),
        "mrr": round(m.mrr, 4),
        "citation_accuracy": round(m.citation_accuracy, 4),
        "faithfulness": round(m.faithfulness, 4),
        "correct_abstention_rate": round(m.correct_abstention_rate, 4),
        "false_abstention_rate": round(m.false_abstention_rate, 4),
        "risk_coverage_auc": round(m.risk_coverage_auc, 4),
        "n_questions": m.n_questions,
        "error_breakdown": m.error_breakdown,
        "cases": [asdict(c) for c in m.cases],
    }


def build_metric_report(
    metrics: list[ConfigMetrics],
    *,
    comparisons: list[dict[str, Any]] | None = None,
    notes: str | None = None,
) -> MetricReport:
    return MetricReport(
        configs=[m.to_contract() for m in metrics],
        comparisons=comparisons or [],
        notes=notes,
    )


def per_question_series(
    metrics: ConfigMetrics,
    metric_name: str,
) -> tuple[list[str], list[float]]:
    """Extract aligned (question_id, score) series used by significance gates."""
    ids: list[str] = []
    values: list[float] = []
    for case in metrics.cases:
        if metric_name == "recall_at_k":
            if case.unanswerable:
                continue
            value = case.recall_at_k
        elif metric_name == "faithfulness":
            value = case.faithfulness
        elif metric_name == "ndcg":
            if case.unanswerable:
                continue
            value = case.ndcg_at_k
        elif metric_name == "mrr":
            if case.unanswerable:
                continue
            value = case.mrr
        elif metric_name == "citation_accuracy":
            value = case.citation_accuracy
        else:
            raise ValueError(f"Unsupported gated metric: {metric_name}")
        if value != value:  # NaN
            continue
        ids.append(case.question_id)
        values.append(float(value))
    return ids, values


def compare_configs_significance(
    metrics: list[ConfigMetrics],
    *,
    metric_names: list[str] | None = None,
    alpha: float = 0.05,
    n_boot: int = 1000,
    seed: int = 42,
    test: str = "paired_bootstrap",
) -> list[dict[str, Any]]:
    """Pairwise significance tests between configs (for the report)."""
    names = metric_names or ["recall_at_k", "faithfulness", "ndcg", "mrr"]
    rows: list[dict[str, Any]] = []
    for i, left in enumerate(metrics):
        for right in metrics[i + 1 :]:
            for metric_name in names:
                left_ids, left_vals = per_question_series(left, metric_name)
                right_ids, right_vals = per_question_series(right, metric_name)
                a, b = align_paired_scores(left_ids, left_vals, right_ids, right_vals)
                # Test whether right regresses vs left (negative delta).
                result = paired_regression_test(
                    b,
                    a,
                    metric=metric_name,
                    alpha=alpha,
                    n_boot=n_boot,
                    seed=seed,
                    test=test,
                )
                rows.append(
                    {
                        "config_a": left.name,
                        "config_b": right.name,
                        "metric": metric_name,
                        "mean_a": result.mean_baseline,
                        "mean_b": result.mean_current,
                        "mean_delta_b_minus_a": result.mean_delta,
                        "p_value": result.p_value,
                        "significant_regression_b_vs_a": result.significant,
                        "alpha": alpha,
                        "test": test,
                        "n": result.n,
                        "delta_ci_low": result.ci_low,
                        "delta_ci_high": result.ci_high,
                    }
                )
    return rows


def baseline_payload(metrics: list[ConfigMetrics]) -> dict[str, Any]:
    """Serializable baseline including per-question scores for significance gates."""
    out: dict[str, Any] = {}
    for m in metrics:
        recall_ids, recall_vals = per_question_series(m, "recall_at_k")
        faith_ids, faith_vals = per_question_series(m, "faithfulness")
        out[m.name] = {
            "chunk_size": m.chunk_size,
            "recall_at_k": round(m.recall_at_k, 4),
            "ndcg": round(m.ndcg, 4),
            "mrr": round(m.mrr, 4),
            "citation_accuracy": round(m.citation_accuracy, 4),
            "faithfulness": round(m.faithfulness, 4),
            "correct_abstention_rate": round(m.correct_abstention_rate, 4),
            "false_abstention_rate": round(m.false_abstention_rate, 4),
            "risk_coverage_auc": round(m.risk_coverage_auc, 4),
            "per_question": {
                "recall_at_k": {"ids": recall_ids, "values": recall_vals},
                "faithfulness": {"ids": faith_ids, "values": faith_vals},
            },
        }
    return out


def compare_to_baseline(
    current_metrics: list[ConfigMetrics],
    baseline: dict[str, Any],
    *,
    alpha: float = 0.05,
    n_boot: int = 1000,
    seed: int = 42,
    test: str = "paired_bootstrap",
    gated_metrics: list[str] | None = None,
) -> list[str]:
    """Fail only on a statistically significant regression vs baseline.

    Test
    ----
    Paired bootstrap (one-sided) on per-question scores, H1: mean(current − baseline) < 0.
    Default α = 0.05. Absolute fixed thresholds are not used.
    """
    gated = gated_metrics or ["recall_at_k", "faithfulness"]
    failures: list[str] = []
    current_by_name = {m.name: m for m in current_metrics}

    for name, cur in current_by_name.items():
        base = baseline.get(name)
        if base is None:
            failures.append(f"{name}: missing from baseline")
            continue
        per_q = base.get("per_question") or {}
        for metric_name in gated:
            cur_ids, cur_vals = per_question_series(cur, metric_name)
            base_series = per_q.get(metric_name) or {}
            base_ids = list(base_series.get("ids") or [])
            base_vals = [float(v) for v in (base_series.get("values") or [])]
            if not base_ids or not base_vals:
                failures.append(
                    f"{name}: baseline lacks per_question.{metric_name} "
                    "(re-run with --write-baseline)"
                )
                continue
            aligned_cur, aligned_base = align_paired_scores(
                cur_ids, cur_vals, base_ids, base_vals
            )
            if len(aligned_cur) < 2:
                failures.append(
                    f"{name}/{metric_name}: fewer than 2 paired questions for significance test"
                )
                continue
            result: PairedTestResult = paired_regression_test(
                aligned_cur,
                aligned_base,
                metric=metric_name,
                alpha=alpha,
                n_boot=n_boot,
                seed=seed,
                test=test,
            )
            if result.significant:
                failures.append(
                    f"{name}: significant regression on {metric_name} "
                    f"(Δ={result.mean_delta:+.4f}, p={result.p_value:.4f}, "
                    f"α={alpha}, test={test})"
                )
    return failures
