# evals-rag-juridique-fr

Harness d'évaluation **RAG** sur un sous-ensemble figé du **Code de la consommation**
(données ouvertes LEGI / DILA).

> **English** — Portfolio-grade offline RAG evaluation harness: frozen French consumer-code
> corpus, 30+5 gold questions, hybrid BM25+embeddings retrieval, local Qwen generator,
> deterministic metrics, chunk-size regression report, and CI over committed generation fixtures.
> No paid APIs.

## Pourquoi

Évaluer un agent RAG juridique de façon **reproductible** et **sans API payante** :
corpus versionné, questions d'or, métriques déterministes, et garde-fous CI.

## Contenu MVP

1. Loader + snapshot d'articles (`data/corpus/`)
2. Gold set FR : 30 questions + 5 non répondables (`data/gold/`)
3. Retrieval hybride BM25 + `multilingual-e5-small` (RRF), chunking configurable
4. Générateur local `qwen2.5:3b-instruct` (Ollama) — citations obligatoires / « je ne sais pas »
5. Métriques : recall@k, abstention, faithfulness (citation + overlap)
6. Comparaison de **deux tailles de chunks** → `reports/regression.md`
7. CI : fixtures de génération commités ; échec si recall/fidélité chutent

## Résultats (baseline)

| Config | chunk_size | recall@5 | faithfulness | abst. correcte | fausse abst. |
|---|---:|---:|---:|---:|---:|
| chunk_500 | 500 | 0.950 | 0.886 | 1.000 | 0.200 |
| chunk_1000 | 1000 | 0.967 | 0.771 | 1.000 | 0.067 |

Détail et commentaire : [`reports/regression.md`](reports/regression.md).
Sur ce petit corpus, `chunk_1000` gagne légèrement en rappel ; `chunk_500` est plus fidèle
(citations + overlap) mais abstient trop souvent sur des questions answerable.

## Installation

Prérequis : Python ≥ 3.11, [uv](https://github.com/astral-sh/uv), [Ollama](https://ollama.com)
(uniquement pour régénérer les fixtures).

```bash
uv sync --extra dev
ollama pull qwen2.5:3b-instruct   # optionnel si --generate
```

## Lancer

```bash
# tests unitaires
uv run pytest -q

# évaluation CI (retrieval + métriques, fixtures générateur)
uv run rag-eval --use-fixtures --check-baseline

# régénérer les réponses avec Ollama + mettre à jour la baseline
uv run rag-eval --generate --write-baseline
```

## Corpus

Sous-ensemble figé du Code de la consommation (`LEGITEXT000006069565`), issu du dump LEGI
DILA (`Freemium_legi_global_20250713-140000.tar.gz`), **Licence Ouverte 2.0**.
Détails : [`data/corpus/SOURCE.md`](data/corpus/SOURCE.md).

## Gold set

- 30 questions answerable + 5 unanswerable
- Toutes marquées `validated: false`
- Échantillon à revoir : [`data/gold/SAMPLE_TO_REVIEW.md`](data/gold/SAMPLE_TO_REVIEW.md)
- Dataset card (HF, non publiée) : [`data/gold/DATASET_CARD.md`](data/gold/DATASET_CARD.md)

## Limites

- Corpus partiel (pas tout le code)
- Questions non encore validées humainement
- Faithfulness heuristique (pas de juge LLM)
- Petit modèle local : réponses parfois approximatives (d'où les fixtures CI)
- Ne constitue **pas** un conseil juridique

## Licence

- Code & gold QA : MIT — voir [`LICENSE`](LICENSE)
- Textes d'articles : Licence Ouverte 2.0 (DILA) — voir `data/corpus/SOURCE.md`
