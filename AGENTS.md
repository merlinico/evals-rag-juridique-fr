# AGENTS.md — guide pour agents / contributeurs automatisés

## Objectif

Harness d'évaluation **RAG** sur un sous-ensemble figé du **Code de la consommation**
(données LEGI / DILA, Licence Ouverte 2.0). Projet personnel open-source (MIT).

## Contraintes non négociables

- Aucune clé d'API payante. Modèles locaux / gratuits uniquement (Ollama, sentence-transformers).
- Ne pas scraper Légifrance hors conditions ; corpus figé versionné dans `data/corpus/`.
- Pas de mention d'employeur / entreprise / side-business dans le code ou la doc.
- README en français d'abord.
- **Contrats gelés** : ne pas modifier `src/rag_juridique/contracts/` ni `schemas/` hors d'un PR
  d'interfaces dédié (voir `CONTRIBUTING.md`).

## Structure

| Chemin | Rôle |
|---|---|
| `src/rag_juridique/contracts/` | **Partagé / gelé** — types + protocoles inter-modules |
| `schemas/` | **Partagé / gelé** — JSON Schema exportés des contrats |
| `data/corpus/` | Snapshot d'articles + `SOURCE.md` (+ versions / cross-refs phase 2) |
| `data/gold/` | Questions d'or + échantillon de revue |
| `data/fixtures/` | Sorties générateur figées pour la CI |
| `src/rag_juridique/corpus/` | Loader corpus, chunking MVP (`FixedSizeChunker`) |
| `src/rag_juridique/gold/` | Chargement du gold set typé |
| `src/rag_juridique/retrieval/` | BM25, dense, hybride (+ rerank / graph phase 2) |
| `src/rag_juridique/generation/` | Prompt + Ollama + lecture fixtures |
| `src/rag_juridique/metrics/` | recall / abstention / faithfulness (+ stats phase 2) |
| `src/rag_juridique/eval/` | CLI + pipeline d'évaluation + rapport |
| `configs/default.yaml` | Chunk sizes, modèles, seuils CI |
| `reports/regression.md` | Rapport de comparaison (2 chunk sizes) |

## Ownership map (phase 2 — 4 agents parallèles)

Chaque agent **possède** les chemins ci-dessous et n'édite pas les chemins des autres.
Les chemins **partagés** ne changent que via un PR d'interfaces (ce freeze) ou avec accord explicite.

| Agent | Module | Possède (écriture) | Ne touche pas |
|---|---|---|---|
| **(a) corpus** | codes + hiérarchie + graphe + versions LEGI | `src/rag_juridique/corpus/` (hors `chunking.py`), `data/corpus/` | `contracts/`, `schemas/`, `data/gold/`, `retrieval/`, `metrics/`, `gold/` |
| **(b) gold** | 150–200 Q, 5 types, filtre auto, batch validation | `src/rag_juridique/gold/`, `data/gold/` | `contracts/`, `schemas/`, `data/corpus/`, `corpus/`, `retrieval/`, `metrics/` |
| **(c) retrieval** | BM25 / dense / hybrid / rerank / graph + 3 chunkers | `src/rag_juridique/retrieval/`, `src/rag_juridique/corpus/chunking.py` | `contracts/`, `schemas/`, `data/corpus/` (lecture seule), `data/gold/` (lecture), `metrics/` |
| **(d) metrics & stats** | recall@k, nDCG, MRR, NLI, CIs, tests de sig., CI gate | `src/rag_juridique/metrics/`, `src/rag_juridique/eval/` (report / gates), `reports/` | `contracts/`, `schemas/`, `data/corpus/`, `data/gold/` (lecture), `retrieval/` (lecture) |

### Partagé — personne n'édite sans PR d'interfaces

- `src/rag_juridique/contracts/**`
- `schemas/**`
- `AGENTS.md`, `CONTRIBUTING.md`, `ROADMAP.md` (coordonner ; pas de feature sneaky)
- `pyproject.toml` / `uv.lock` : n'ajouter une dépendance que dans le module propriétaire ; résoudre les conflits de lock en rebase
- `configs/default.yaml` : chaque agent peut ajouter **sa** section (`corpus:`, `gold:`, `retrieval:`, `metrics:`) sans renommer les clés existantes
- `data/fixtures/` : régénérés hors CI (GPU local) ; format = `GenerationRecord` ; l'agent qui change le générateur / la config de gen met à jour les fixtures + baseline
- `src/rag_juridique/generation/` : partagé léger ; changements de format de fixture = contrat `GenerationRecord`

### Frontières API (rappel)

- Corpus produit `Article` / `ArticleVersion` / `CrossRef` consommés en lecture.
- Gold produit `Question` (`type`, `expected_article_ids`, `as_of`, `validated`).
- Retrieval implémente `Retriever.retrieve(query, k, as_of=None) -> list[RetrievedChunk]` et `Chunker.chunk(...)`.
- Metrics consomme gold + hits + `GenerationRecord` ; publie `MetricResult` / `MetricReport`.
- Génération lourde (7–8B) : une fois hors CI → fixtures `GenerationRecord`.

## Commandes utiles

```bash
uv sync --extra dev
uv run pytest -q
# Régénérer les JSON Schema depuis les modèles Pydantic
uv run python -m rag_juridique.contracts.export_schemas
# Génération locale (Ollama + qwen2.5:3b-instruct)
uv run rag-eval --generate --write-baseline
# Mode CI (fixtures uniquement)
uv run rag-eval --use-fixtures --check-baseline
```

## Métriques

- `passage recall@k` : déterministe sur les ids d'articles.
- Abstention : taux correct sur unanswerables vs fausse abstention sur answerables.
- Faithfulness : citation obligatoire + article cité dans le contexte + overlap lexical (pas de LLM-as-judge).
- Phase 2 (agent d) : nDCG, MRR, NLI local FR, risk-coverage, bootstrap CI, tests de significance ;
  la CI échoue sur une **baisse statistiquement significative**, pas un seuil fixe seul.

## Coupes autorisées (si manque de temps)

1. Reranking cross-encoder → `ROADMAP.md`
2. Jurisprudence
3. HF Space (garder la dataset card)
4. Garder 30 questions (pas 50)

Ne jamais couper : rapport de régression, questions unanswerable, CI fixtures, contrats gelés.
