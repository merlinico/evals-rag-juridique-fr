from __future__ import annotations

from rag_juridique.retrieval.hybrid import RetrievalResult

ABSTENTION_PHRASE = "je ne sais pas"

SYSTEM_PROMPT = """Tu es un assistant juridique prudent, spécialisé dans le Code de la consommation français.
Tu réponds UNIQUEMENT à partir des extraits fournis (contexte).

Règles strictes :
1. Cite toujours les identifiants d'articles utilisés, au format [L. XXX-Y] (numéro d'article).
2. Si le contexte ne permet pas de répondre de façon fiable, réponds exactement : « je ne sais pas ».
3. N'invente aucune règle, délai, sanction ou exception absente du contexte.
4. Réponds en français, de façon concise (2 à 5 phrases).
5. Termine par une ligne « Citations : » listant les articles cités, séparés par des virgules.
"""


def build_rag_prompt(question: str, hits: list[RetrievalResult]) -> str:
    blocks: list[str] = []
    for i, hit in enumerate(hits, start=1):
        c = hit.chunk
        blocks.append(
            f"[Extrait {i}] Article {c.article_num} (id={c.article_id})\n{c.text}"
        )
    context = "\n\n".join(blocks) if blocks else "(aucun extrait)"
    return (
        f"{SYSTEM_PROMPT}\n\n"
        f"## Contexte\n{context}\n\n"
        f"## Question\n{question}\n\n"
        f"## Réponse\n"
    )
