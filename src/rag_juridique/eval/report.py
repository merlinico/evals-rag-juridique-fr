from __future__ import annotations

from pathlib import Path
from typing import Any

from rag_juridique.eval.pipeline import ConfigMetrics


def render_regression_report(
    metrics: list[ConfigMetrics],
    *,
    recall_k: int,
    notes: str = "",
) -> str:
    lines: list[str] = [
        "# Rapport de régression RAG — Code de la consommation",
        "",
        "Comparaison de deux tailles de chunks (fusion hybride BM25 + embeddings).",
        "",
        f"Métrique de rappel : **passage recall@{recall_k}** (ids d'articles).",
        "Fidélité : citation obligatoire + article cité présent dans le contexte + chevauchement lexical.",
        "",
        "## Tableau",
        "",
        "| Config | chunk_size | recall@k | faithfulness | abstention correcte (unans.) | fausse abstention (ans.) |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for m in metrics:
        lines.append(
            f"| {m.name} | {m.chunk_size} | {m.recall_at_k:.3f} | {m.faithfulness:.3f} | "
            f"{m.correct_abstention_rate:.3f} | {m.false_abstention_rate:.3f} |"
        )

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
            f"- Meilleure fidélité (citation + overlap) : **{better_faith}** "
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
    if notes:
        lines.extend(["", notes, ""])
    lines.extend(
        [
            "",
            "## Limites",
            "",
            "- Jeu d'or non encore validé humainement (`validated: false`).",
            "- Fidélité fondée sur des heuristiques (pas de LLM-as-judge).",
            "- Générateur local petit : les fixtures CI figent ses sorties.",
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
            "faithfulness": round(m.faithfulness, 4),
            "correct_abstention_rate": round(m.correct_abstention_rate, 4),
            "false_abstention_rate": round(m.false_abstention_rate, 4),
        }
        for m in metrics
    }
