from rag_juridique.eval.pipeline import (
    ConfigCaseResult,
    ConfigMetrics,
    compare_to_baseline,
)


def _metrics(name: str, recalls: list[float], faiths: list[float]) -> ConfigMetrics:
    cases = []
    for i, (r, f) in enumerate(zip(recalls, faiths)):
        cases.append(
            ConfigCaseResult(
                question_id=f"q{i}",
                question_type="direct",
                unanswerable=False,
                recall_at_k=r,
                ndcg_at_k=r,
                mrr=r,
                retrieved_article_ids=[],
                faithfulness=f,
                citation_accuracy=f,
                abstained=False,
                confidence=0.5,
                answer="x",
            )
        )
    return ConfigMetrics(
        name=name,
        chunk_size=500,
        recall_at_k=sum(recalls) / len(recalls),
        ndcg=sum(recalls) / len(recalls),
        mrr=sum(recalls) / len(recalls),
        citation_accuracy=sum(faiths) / len(faiths),
        faithfulness=sum(faiths) / len(faiths),
        correct_abstention_rate=1.0,
        false_abstention_rate=0.0,
        risk_coverage_auc=0.1,
        n_questions=len(cases),
        cases=cases,
    )


def test_gate_passes_without_significant_regression():
    cur = _metrics("chunk_500", [1, 1, 1, 0, 1, 1, 1, 1], [1, 1, 0, 1, 1, 1, 1, 1])
    baseline = {
        "chunk_500": {
            "recall_at_k": 0.875,
            "faithfulness": 0.875,
            "per_question": {
                "recall_at_k": {
                    "ids": [f"q{i}" for i in range(8)],
                    "values": [1, 1, 1, 0, 1, 1, 1, 1],
                },
                "faithfulness": {
                    "ids": [f"q{i}" for i in range(8)],
                    "values": [1, 1, 0, 1, 1, 1, 1, 1],
                },
            },
        }
    }
    failures = compare_to_baseline([cur], baseline, alpha=0.05, n_boot=300, seed=0)
    assert failures == []


def test_gate_fails_on_significant_regression():
    cur = _metrics("chunk_500", [0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0, 0])
    baseline = {
        "chunk_500": {
            "recall_at_k": 1.0,
            "faithfulness": 1.0,
            "per_question": {
                "recall_at_k": {
                    "ids": [f"q{i}" for i in range(8)],
                    "values": [1, 1, 1, 1, 1, 1, 1, 1],
                },
                "faithfulness": {
                    "ids": [f"q{i}" for i in range(8)],
                    "values": [1, 1, 1, 1, 1, 1, 1, 1],
                },
            },
        }
    }
    failures = compare_to_baseline([cur], baseline, alpha=0.05, n_boot=300, seed=0)
    assert failures
    assert any("significant regression" in f for f in failures)


def test_gate_ignores_small_non_significant_noise():
    # Tiny one-flip change on N=8 is usually not significant at α=0.05.
    cur = _metrics("chunk_500", [1, 1, 1, 1, 1, 1, 1, 0], [1] * 8)
    baseline = {
        "chunk_500": {
            "per_question": {
                "recall_at_k": {
                    "ids": [f"q{i}" for i in range(8)],
                    "values": [1, 1, 1, 1, 1, 1, 1, 1],
                },
                "faithfulness": {
                    "ids": [f"q{i}" for i in range(8)],
                    "values": [1] * 8,
                },
            }
        }
    }
    failures = compare_to_baseline([cur], baseline, alpha=0.05, n_boot=400, seed=3)
    # Absolute drop exists, but must not fail without significance.
    assert not any("recall_at_k" in f and "significant" in f for f in failures)
