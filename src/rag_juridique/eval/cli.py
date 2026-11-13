from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from rag_juridique.eval.pipeline import (
    baseline_payload,
    build_metric_report,
    compare_configs_significance,
    compare_to_baseline,
    load_config,
    metrics_to_dict,
    run_config,
)
from rag_juridique.eval.report import (
    GATE_DOCUMENTATION,
    render_regression_report,
    summary_table_dict,
    write_report,
)
from rag_juridique.gold.loader import load_gold


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="rag-eval",
        description="Harness d'évaluation RAG — Code de la consommation",
    )
    parser.add_argument(
        "--config",
        default="configs/default.yaml",
        help="Chemin vers la config YAML",
    )
    parser.add_argument(
        "--generate",
        action="store_true",
        help="Appeler Ollama pour générer les réponses (et écrire des fixtures)",
    )
    parser.add_argument(
        "--use-fixtures",
        action="store_true",
        help="Utiliser les fixtures de génération commités (mode CI)",
    )
    parser.add_argument(
        "--check-baseline",
        action="store_true",
        help="Échouer sur régression statistiquement significative vs baseline",
    )
    parser.add_argument(
        "--write-baseline",
        action="store_true",
        help="Écrire data/fixtures/baseline_metrics.json à partir des métriques courantes",
    )
    args = parser.parse_args(argv)

    config = load_config(args.config)
    gold = load_gold(config["gold_path"])
    sizes = list(config["chunking"]["sizes"])
    fixtures_dir = Path(config["generation"]["fixtures_dir"])
    fixtures_dir.mkdir(parents=True, exist_ok=True)
    metrics_cfg = config.get("metrics", {})

    # Share one embedding model across configs for speed.
    from sentence_transformers import SentenceTransformer

    dense_model = SentenceTransformer(config["retrieval"]["embedding_model"])

    all_metrics = []
    all_summaries: dict[str, Any] = {}

    for size in sizes:
        name = f"chunk_{size}"
        fixture_path = fixtures_dir / f"generations_{name}.json"
        metrics, generations = run_config(
            name=name,
            chunk_size=int(size),
            config=config,
            gold=gold,
            use_fixtures=args.use_fixtures,
            fixtures_path=fixture_path,
            generate=args.generate,
            dense_model=dense_model,
        )
        all_metrics.append(metrics)
        all_summaries[name] = {
            k: v for k, v in metrics_to_dict(metrics).items() if k != "cases"
        }
        if args.generate and generations:
            payload = {
                "config": name,
                "chunk_size": size,
                "model": config["generation"]["model"],
                "generations": generations,
            }
            fixture_path.write_text(
                json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            print(f"Wrote fixtures: {fixture_path}")

    alpha = float(metrics_cfg.get("significance_alpha", 0.05))
    n_boot = int(metrics_cfg.get("bootstrap_n", 1000))
    seed = int(metrics_cfg.get("bootstrap_seed", 42))
    test_name = str(metrics_cfg.get("significance_test", "paired_bootstrap"))
    comparisons = compare_configs_significance(
        all_metrics,
        alpha=alpha,
        n_boot=n_boot,
        seed=seed,
        test=test_name,
    )
    report = render_regression_report(
        all_metrics,
        recall_k=int(metrics_cfg.get("recall_k", 5)),
        comparisons=comparisons,
        gate_doc=GATE_DOCUMENTATION,
    )
    report_path = Path(config["report"]["output_path"])
    write_report(report_path, report)
    print(report)
    print(f"\nReport written to {report_path}")

    metric_report = build_metric_report(
        all_metrics,
        comparisons=comparisons,
        notes="phase-2 metrics + paired bootstrap significance",
    )
    report_json_path = fixtures_dir / "last_metric_report.json"
    report_json_path.write_text(
        metric_report.model_dump_json(indent=2),
        encoding="utf-8",
    )

    summary_path = fixtures_dir / "last_metrics.json"
    summary_path.write_text(
        json.dumps(summary_table_dict(all_metrics), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    if args.write_baseline:
        baseline_path = Path(config["report"]["baseline_path"])
        baseline_path.parent.mkdir(parents=True, exist_ok=True)
        baseline_path.write_text(
            json.dumps(baseline_payload(all_metrics), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        print(f"Wrote baseline: {baseline_path}")

    if args.check_baseline:
        baseline_path = Path(config["report"]["baseline_path"])
        if not baseline_path.exists():
            print(f"Baseline missing: {baseline_path}", file=sys.stderr)
            return 2
        baseline = json.loads(baseline_path.read_text(encoding="utf-8"))
        failures = compare_to_baseline(
            all_metrics,
            baseline,
            alpha=alpha,
            n_boot=n_boot,
            seed=seed,
            test=test_name,
            gated_metrics=list(
                metrics_cfg.get("gated_metrics") or ["recall_at_k", "faithfulness"]
            ),
        )
        if failures:
            print("BASELINE CHECK FAILED:", file=sys.stderr)
            for item in failures:
                print(f" - {item}", file=sys.stderr)
            return 1
        print(
            f"Baseline check passed "
            f"(paired bootstrap, α={alpha}, no significant regression)."
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
