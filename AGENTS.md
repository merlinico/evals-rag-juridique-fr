# AGENTS.md — guide pour agents / contributeurs automatisés

## Objectif

Harness d'évaluation **RAG** sur un sous-ensemble figé du **Code de la consommation**
(données LEGI / DILA, Licence Ouverte 2.0). Projet personnel open-source (MIT).

## Contraintes non négociables

- Aucune clé d'API payante. Modèles locaux / gratuits uniquement (Ollama, sentence-transformers).
- Ne pas scraper Légifrance hors conditions ; corpus figé versionné dans `data/corpus/`.
- Pas de mention d'employeur / entreprise / side-business dans le code ou la doc.
- README en français d'abord.

## Structure

| Chemin | Rôle |
|---|---|
| `data/corpus/` | Snapshot d'articles + `SOURCE.md` |
| `data/gold/` | Questions d'or + échantillon de revue |
| `data/fixtures/` | Sorties générateur figées pour la CI |
| `src/rag_juridique/` | Loader, chunking, retrieval, génération, métriques, CLI |
| `configs/default.yaml` | Chunk sizes, modèles, seuils CI |
| `reports/regression.md` | Rapport de comparaison (2 chunk sizes) |

## Commandes utiles

```bash
uv sync --extra dev
uv run pytest -q
# Génération locale (Ollama + qwen2.5:3b-instruct)
uv run rag-eval --generate --write-baseline
# Mode CI (fixtures uniquement)
uv run rag-eval --use-fixtures --check-baseline
```

## Métriques

- `passage recall@k` : déterministe sur les ids d'articles.
- Abstention : taux correct sur unanswerables vs fausse abstention sur answerables.
- Faithfulness : citation obligatoire + article cité dans le contexte + overlap lexical (pas de LLM-as-judge).

## Coupes autorisées (si manque de temps)

1. Reranking cross-encoder → `ROADMAP.md`
2. Jurisprudence
3. HF Space (garder la dataset card)
4. Garder 30 questions (pas 50)

Ne jamais couper : rapport de régression, questions unanswerable, CI fixtures.
