"""Stratified human-review batch (40) + markdown rendering."""

from __future__ import annotations

from collections import defaultdict
from pathlib import Path

from rag_juridique.contracts.corpus import Article
from rag_juridique.contracts.gold import Question, QuestionType
from rag_juridique.gold.textutil import snippet

# Fold in the existing SAMPLE_TO_REVIEW items first.
SAMPLE_TO_REVIEW_IDS = [
    "q08",
    "q11",
    "q14",
    "q06",
    "q05",
    "q23",
    "q21",
    "q18",
    "u01",
    "u05",
]


def select_review_batch(
    questions: list[Question],
    *,
    size: int = 40,
    must_include: list[str] | None = None,
) -> list[Question]:
    must = list(must_include or SAMPLE_TO_REVIEW_IDS)
    by_id = {q.id: q for q in questions}
    chosen: list[Question] = []
    seen: set[str] = set()

    for qid in must:
        q = by_id.get(qid)
        if q is not None and qid not in seen:
            chosen.append(q)
            seen.add(qid)

    # Stratify remaining slots across the 5 types.
    remaining_slots = size - len(chosen)
    if remaining_slots <= 0:
        return chosen[:size]

    per_type: dict[str, list[Question]] = defaultdict(list)
    for q in questions:
        if q.id in seen:
            continue
        per_type[q.type.value].append(q)

    type_order = [t.value for t in QuestionType]
    # Round-robin until filled, preferring types still missing in the batch.
    present = {q.type.value for q in chosen}
    # First ensure every type appears at least once if possible.
    for t in type_order:
        if remaining_slots <= 0:
            break
        if t not in present and per_type[t]:
            q = per_type[t].pop(0)
            chosen.append(q)
            seen.add(q.id)
            present.add(t)
            remaining_slots -= 1

    idx = 0
    while remaining_slots > 0:
        progressed = False
        for t in type_order:
            if remaining_slots <= 0:
                break
            if per_type[t]:
                q = per_type[t].pop(0)
                chosen.append(q)
                seen.add(q.id)
                remaining_slots -= 1
                progressed = True
        if not progressed:
            break
        idx += 1
        if idx > 1000:
            break

    return chosen[:size]


def render_review_markdown(
    batch: list[Question],
    articles: list[Article],
    *,
    title: str = "Batch de revue humaine (40 questions)",
) -> str:
    by_id = {a.id: a for a in articles}
    lines: list[str] = [
        f"# {title}",
        "",
        "Toutes les questions du jeu d'or restent `validated: false` jusqu'à revue.",
        "Ce batch est **stratifié** sur les 5 `QuestionType` et **inclut** les items",
        "de `SAMPLE_TO_REVIEW.md`.",
        "",
        "Légende du verdict : **OK** / **À corriger** / **À reformuler**.",
        "",
        "## Index",
        "",
        "| id | type | topic | verdict |",
        "|---|---|---|---|",
    ]
    for q in batch:
        topic = q.topic or "—"
        lines.append(f"| {q.id} | `{q.type.value}` | {topic} | |")

    lines.extend(["", "## Détail pour validation rapide", ""])

    for i, q in enumerate(batch, 1):
        lines.append(f"### {i}. `{q.id}` — `{q.type.value}`")
        lines.append("")
        lines.append(f"**Question :** {q.question}")
        lines.append("")
        if q.as_of is not None:
            lines.append(f"**as_of :** `{q.as_of.isoformat()}`")
            lines.append("")
        if q.unanswerable or q.type == QuestionType.UNANSWERABLE:
            lines.append("**Articles gold :** — (unanswerable / hors corpus)")
            lines.append("")
            lines.append(f"**Réponse attendue :** {q.reference_answer or 'je ne sais pas'}")
        else:
            nums = ", ".join(q.expected_article_nums) or "—"
            ids = ", ".join(q.expected_article_ids)
            lines.append(f"**Articles gold :** {nums}")
            lines.append("")
            lines.append(f"**Ids LEGIARTI :** `{ids}`")
            lines.append("")
            lines.append(f"**Réponse attendue :** {q.reference_answer or '—'}")
            lines.append("")
            lines.append("**Extraits corpus :**")
            lines.append("")
            for aid in q.expected_article_ids:
                art = by_id.get(aid)
                if art is None:
                    lines.append(f"- `{aid}` : *(absent du snapshot)*")
                    continue
                lines.append(f"- **{art.num}** (`{art.id}`) — {snippet(art.text, 320)}")
        if q.notes:
            lines.append("")
            lines.append(f"*Notes :* {q.notes}")
        lines.extend(["", "Verdict : ☐ OK ☐ À corriger ☐ À reformuler", "", "---", ""])

    lines.extend(
        [
            "## Checklist",
            "",
            "1. La réponse de référence est supportée par le(s) article(s) gelé(s).",
            "2. Pas d'ambiguïté majeure (autres articles également valides non listés).",
            "3. `multi_hop` : les deux (ou plus) articles sont nécessaires.",
            "4. `temporal` : la réponse est correcte à la date `as_of`.",
            "5. `unanswerable` : non répondable avec le snapshot courant.",
            "6. `apparent_contradiction` : le « conflit » se résout par articulation des textes.",
            "7. Passer `validated: true` question par question dans `questions.json` après revue.",
            "",
        ]
    )
    return "\n".join(lines)


def write_review_batch(
    path: Path | str,
    batch: list[Question],
    articles: list[Article],
) -> Path:
    out = Path(path)
    out.write_text(render_review_markdown(batch, articles), encoding="utf-8")
    return out
