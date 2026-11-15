from __future__ import annotations

from pathlib import Path
from typing import Any

from rag_juridique.eval.pipeline import ConfigMetrics


def _fmt_ci(low: float | None, high: float | None) -> str:
    if low is None or high is None:
        return "—"
    return f"[{low:.3f}, {high:.3f}]"


def _metric_lookup(m: ConfigMetrics) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for result in m.metric_results:
        key = result.name.value if hasattr(result.name, "value") else str(result.name)
        out[key] = result
    return out


def render_regression_report(
    metrics: list[ConfigMetrics],
    *,
    recall_k: int,
    comparisons: list[dict[str, Any]] | None = None,
    notes: str = "",
    gate_doc: str = "",
) -> str:
    lines: list[str] = [
        "# Rapport de régression RAG — Code de la consommation",
        "",
        "Comparaison de configs (fusion hybride BM25 + embeddings) avec métriques phase 2,",
        "intervalles de confiance bootstrap et tests de significance appariés.",
        "",
        f"Métriques de ranking : **recall@{recall_k}**, **nDCG@{recall_k}**, **MRR**.",
        "Citation accuracy : précision des articles cités vs contexte récupéré.",
        "Fidélité : overlap lexical (CI) ; NLI claim-level FR optionnel hors CI.",
        "Abstention : taux correct / fausse abstention + courbe **risk-coverage**.",
        "",
        "## Tableau",
        "",
        "| Config | chunk | recall@k | nDCG | MRR | citation | faithfulness | abst. OK | fausse abst. | RC-AUC |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for m in metrics:
        lines.append(
            f"| {m.name} | {m.chunk_size} | {m.recall_at_k:.3f} | {m.ndcg:.3f} | "
            f"{m.mrr:.3f} | {m.citation_accuracy:.3f} | {m.faithfulness:.3f} | "
            f"{m.correct_abstention_rate:.3f} | {m.false_abstention_rate:.3f} | "
            f"{m.risk_coverage_auc:.3f} |"
        )

    lines.extend(["", "## Intervalles de confiance (bootstrap)", ""])
    for m in metrics:
        lookup = _metric_lookup(m)
        lines.append(f"### {m.name}")
        lines.append("")
        lines.append("| Métrique | valeur | IC | n |")
        lines.append("|---|---:|---|---:|")
        for key in (
            "recall_at_k",
            "ndcg",
            "mrr",
            "citation_accuracy",
            "faithfulness",
            "correct_abstention_rate",
            "false_abstention_rate",
            "risk_coverage",
        ):
            result = lookup.get(key)
            if result is None:
                continue
            lines.append(
                f"| {key} | {result.value:.3f} | {_fmt_ci(result.ci_low, result.ci_high)} | "
                f"{result.n if result.n is not None else '—'} |"
            )
        lines.append("")

    lines.extend(["", "## Erreurs par type de question", ""])
    for m in metrics:
        lines.append(f"### {m.name}")
        lines.append("")
        if not m.error_breakdown:
            lines.append("_Aucune ventilation disponible._")
            lines.append("")
            continue
        lines.append(
            "| type | n | error_rate | recall | faith | citation | miss retr. | fausse abst. | cite KO |"
        )
        lines.append("|---|---:|---:|---:|---:|---:|---:|---:|---:|")
        for qtype, row in m.error_breakdown.items():
            lines.append(
                f"| {qtype} | {row['n']} | {row['error_rate']:.3f} | "
                f"{row['mean_recall'] if row['mean_recall'] is not None else '—'} | "
                f"{row['mean_faithfulness'] if row['mean_faithfulness'] is not None else '—'} | "
                f"{row['mean_citation_accuracy'] if row['mean_citation_accuracy'] is not None else '—'} | "
                f"{row['missed_retrieval']} | {row['false_abstentions']} | "
                f"{row['unsupported_citation']} |"
            )
        lines.append("")

    if comparisons:
        lines.extend(["", "## Tests de significance entre configs", ""])
        lines.append(
            "Test apparié bootstrap unilatéral : H1 = la config B régresse vs A "
            "(mean Δ < 0), α documenté ci-dessous."
        )
        lines.append("")
        lines.append(
            "| A | B | métrique | mean A | mean B | Δ (B−A) | p | significatif | n |"
        )
        lines.append("|---|---|---|---:|---:|---:|---:|---|---:|")
        for row in comparisons:
            sig = "oui" if row.get("significant_regression_b_vs_a") else "non"
            lines.append(
                f"| {row['config_a']} | {row['config_b']} | {row['metric']} | "
                f"{row['mean_a']:.3f} | {row['mean_b']:.3f} | "
                f"{row['mean_delta_b_minus_a']:+.3f} | {row['p_value']:.3f} | "
                f"{sig} | {row['n']} |"
            )
        lines.append("")

    lines.extend(["", "## Commentaire", ""])
    if len(metrics) >= 2:
        a, b = metrics[0], metrics[1]
        better_recall = a.name if a.recall_at_k >= b.recall_at_k else b.name
        better_faith = a.name if a.faithfulness >= b.faithfulness else b.name
        lines.append(
            f"- Meilleur rappel : **{better_recall}** "
            f"({max(a.recall_at_k, b.recall_at_k):.3f})."
        )
        lines.append(
            f"- Meilleure fidélité : **{better_faith}** "
            f"({max(a.faithfulness, b.faithfulness):.3f})."
        )
        delta = b.recall_at_k - a.recall_at_k
        lines.append(
            f"- Écart de recall@{recall_k} ({b.name} − {a.name}) : {delta:+.3f}."
        )
        if abs(delta) < 0.03:
            lines.append(
                "- Les deux chunk sizes sont proches sur ce petit corpus gelé ; "
                "des écarts plus nets sont attendus avec un corpus plus large ou un reranker."
            )
        elif delta > 0:
            lines.append(
                f"- Les chunks plus grands ({b.chunk_size}) capturent mieux les articles "
                "complets sur ce jeu, au prix d'un contexte plus bruyant pour le générateur."
            )
        else:
            lines.append(
                f"- Les chunks plus petits ({a.chunk_size}) améliorent ici le ranking "
                "en réduisant le bruit lexical dans chaque passage."
            )

    if gate_doc:
        lines.extend(["", "## Gate CI (significance)", "", gate_doc, ""])

    if notes:
        lines.extend(["", notes, ""])

    lines.extend(
        [
            "",
            "## Limites",
            "",
            "- Jeu d'or partiellement validé humainement (batch 40 `validated: true` ; reste `false`).",
            "- Fidélité CI = heuristique overlap ; NLI FR local optionnel (`metrics.nli_enabled`).",
            "- Générateur local : fixtures CI figent ses sorties ; regen 7B hors CI (voir `RUN_ON_GPU.md`).",
            "- Bootstrap sur N≈30 : les IC sont larges ; le gate exige une régression significative.",
            "",
        ]
    )
    return "\n".join(lines)


def write_report(path: Path | str, content: str) -> None:
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(content, encoding="utf-8")


def summary_table_dict(metrics: list[ConfigMetrics]) -> dict[str, Any]:
    return {
        m.name: {
            "chunk_size": m.chunk_size,
            "recall_at_k": round(m.recall_at_k, 4),
            "ndcg": round(m.ndcg, 4),
            "mrr": round(m.mrr, 4),
            "citation_accuracy": round(m.citation_accuracy, 4),
            "faithfulness": round(m.faithfulness, 4),
            "correct_abstention_rate": round(m.correct_abstention_rate, 4),
            "false_abstention_rate": round(m.false_abstention_rate, 4),
            "risk_coverage_auc": round(m.risk_coverage_auc, 4),
        }
        for m in metrics
    }


GATE_DOCUMENTATION = """\
La CI échoue **uniquement** si une métrique gate (`recall_at_k`, `faithfulness`)
présente une **régression statistiquement significative** vs `baseline_metrics.json`.

- **Test** : bootstrap apparié unilatéral sur scores par question
  (`paired_bootstrap`), H1 : mean(current − baseline) < 0
- **α** : `metrics.significance_alpha` (défaut **0.05**)
- Les seuils absolus fixes (`min_recall_at_k` / `min_faithfulness`) ne sont plus
  utilisés comme critère d'échec.
"""
