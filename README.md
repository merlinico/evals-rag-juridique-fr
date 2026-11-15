# evals-rag-juridique-fr

Harness d'évaluation **RAG** sur un sous-ensemble figé du **Code de la consommation**
(données ouvertes LEGI / DILA).

> **English** — Portfolio-grade offline RAG evaluation harness: frozen French consumer-code
> corpus, 180 gold questions (151 answerable + 29 unanswerable; 40 hand-validated),
> hybrid BM25+embeddings retrieval, local Qwen 7B generator fixtures, deterministic
> metrics, chunk-size regression report, and CI over committed generation fixtures.
> No paid APIs.

## Pourquoi

Évaluer un agent RAG juridique de façon **reproductible** et **sans API payante** :
corpus versionné, questions d'or, métriques déterministes, et garde-fous CI.

## Contenu

1. Loader + snapshot d'articles (`data/corpus/`)
2. Gold set FR : **180** questions (151 answerable + 29 non répondables) — 40 `validated: true`
3. Retrieval hybride BM25 + `multilingual-e5-small` (RRF), chunking configurable
4. Générateur local `qwen2.5:7b-instruct` (Ollama) — fixtures commités ; citations / « je ne sais pas »
5. Métriques : recall@k, nDCG, MRR, abstention, faithfulness (citation + overlap), CIs bootstrap
6. Comparaison de **deux tailles de chunks** → `reports/regression.md`
7. CI : fixtures de génération commités ; échec si régression statistiquement significative
8. Contrats gelés inter-modules (`src/rag_juridique/contracts/`, `schemas/`) — ownership dans `AGENTS.md`

## Résultats (15 nov 2026)

Source : run Talos / PC local, commit fixtures [`935c197`](https://github.com/merlinico/evals-rag-juridique-fr/commit/935c197)
(`data/talos-run-2026-11-15`), régénéré côté harness avec
`uv run rag-eval --use-fixtures --write-baseline`.

| | |
|---|---|
| **Date** | 2026-11-15 |
| **Modèle** | `qwen2.5:7b-instruct` (Ollama) |
| **Corpus** | `data/corpus/eval_subset.json.gz` (LEGI DILA 2025-07-13, Licence Ouverte 2.0) |
| **Gold** | 180 questions = 151 answerable + 29 unanswerable (`data/gold/questions.json`) |
| **Validation humaine** | **40 / 180** marquées `validated: true` (batch `REVIEW_BATCH_40`, 2026-11-14) |
| **Retrieval CI** | hybrid BM25 + `multilingual-e5-small`, configs `chunk_500` / `chunk_1000` |

### Jeu complet (180 Q)

| Config | chunk_size | recall@5 | faithfulness | abst. correcte | fausse abst. |
|---|---:|---:|---:|---:|---:|
| chunk_500 | 500 | 0.483 | 0.972 | 1.000 | 0.609 |
| chunk_1000 | 1000 | 0.483 | 0.967 | 1.000 | 0.609 |

### Sous-ensemble validé (40 Q, `validated: true`)

Métriques recalculées sur les 40 questions du batch (34 answerable + 6 unanswerable),
mêmes fixtures / même retrieval que ci-dessus.

| Config | chunk_size | recall@5 | faithfulness | abst. correcte | fausse abst. |
|---|---:|---:|---:|---:|---:|
| chunk_500 | 500 | 0.603 | 0.975 | 1.000 | 0.471 |
| chunk_1000 | 1000 | 0.632 | 0.950 | 1.000 | 0.441 |

Détail (nDCG, MRR, CIs, erreurs par type, tests de significance) :
[`reports/regression.md`](reports/regression.md).

Sur le jeu complet, les deux chunk sizes sont proches en rappel ; `chunk_500` reste
légèrement plus fidèle. Le rappel chute surtout sur `multi_hop` et `temporal`
(fausse abstention élevée). Sur le batch validé, le rappel est plus haut (~0.60–0.63)
car le batch est plus riche en questions `direct`.

### Configs retrieval lourdes — non calculées

Les configs `RAG_HEAVY=1` (bge-m3, rerank, graph, etc. — voir `RUN_ON_GPU.md` §2)
**n'ont pas produit de résultats** : le run Talos du 15 nov 2026 a crashé
(exit `-1073741819`, aucun artefact). Aucun chiffre inventé ici ; à relancer
hors CI quand le GPU / encodeurs lourds sont stables.

## Installation

Prérequis : Python ≥ 3.11, [uv](https://github.com/astral-sh/uv), [Ollama](https://ollama.com)
(uniquement pour régénérer les fixtures).

```bash
uv sync --extra dev
ollama pull qwen2.5:7b-instruct   # optionnel si regen GPU — voir RUN_ON_GPU.md
```

## Lancer

```bash
# tests unitaires
uv run pytest -q

# évaluation CI (retrieval + métriques, fixtures générateur)
uv run rag-eval --use-fixtures --check-baseline

# régénérer les réponses avec Ollama + mettre à jour la baseline (hors CI / GPU)
uv run python scripts/generate_offline.py --model qwen2.5:7b-instruct --write-baseline
```

## Corpus

Sous-ensemble figé du Code de la consommation (`LEGITEXT000006069565`), issu du dump LEGI
DILA (`Freemium_legi_global_20250713-140000.tar.gz`), **Licence Ouverte 2.0**.
Détails : [`data/corpus/SOURCE.md`](data/corpus/SOURCE.md).

## Gold set

- **180** questions : 151 answerable + 29 unanswerable
- **40** marquées `validated: true` (`REVIEW_BATCH_40`, validé 2026-11-14) ; le reste `validated: false`
- Batch de revue : [`data/gold/REVIEW_BATCH_40.md`](data/gold/REVIEW_BATCH_40.md)
- Dataset card (HF, non publiée) : [`data/gold/DATASET_CARD.md`](data/gold/DATASET_CARD.md)

## Limites

- Corpus partiel (pas tout le code)
- Seules 40 / 180 questions validées humainement
- Faithfulness heuristique (pas de juge LLM) en CI ; NLI local optionnel hors CI
- Générateur local 7B : réponses figées en fixtures pour la CI
- Retrieval lourd (bge-m3 / rerank / graph) non mesuré (crash run 2026-11-15)
- Ne constitue **pas** un conseil juridique

## Licence

- Code & gold QA : MIT — voir [`LICENSE`](LICENSE)
- Textes d'articles : Licence Ouverte 2.0 (DILA) — voir `data/corpus/SOURCE.md`
