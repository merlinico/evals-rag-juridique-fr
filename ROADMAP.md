# ROADMAP

## Fait (MVP foundations)

- [x] Corpus figé Code de la consommation + attribution Licence Ouverte
- [x] Gold set 30 + 5 unanswerables (`validated: false`)
- [x] Retrieval hybride BM25 + multilingual-e5 + RRF
- [x] Générateur local Qwen2.5 3B (Ollama) + fixtures CI
- [x] Métriques recall@k / abstention / faithfulness heuristique
- [x] Comparaison 2 chunk sizes + rapport markdown
- [x] CI GitHub Actions avec seuils vs baseline
- [x] **Freeze des contrats** inter-modules (`contracts/` + `schemas/` + ownership)

## Phase 2 — 4 tâches agent (parallèles après le freeze)

Les agents démarrent **après** merge du PR de contrats. Dépendances = contrats + lecture des artefacts amont ; pas d'édition croisée (voir `AGENTS.md`).

### (a) Corpus — codes, hiérarchie, graphe, versions

**Possède :** `src/rag_juridique/corpus/` (hors `chunking.py`), `data/corpus/`

**Livrables**
- Étendre le snapshot : codes **civil**, **consommation**, **travail**
- Hiérarchie `livre` / `titre` / `chapitre` / `article` peuplée sur `Article`
- Graphe `CrossRef` (citations / renvois entre articles), fichier versionné
- Historique LEGI : `ArticleVersion` + résolution « version en vigueur à une date »

**Critères d'acceptation**
- JSON / loaders valident les schémas `Article`, `ArticleVersion`, `CrossRef`
- Ids LEGIARTI du gold MVP restent stables (pas de rename cassant)
- API : `load_corpus` (+ helpers version / graphe) documentée ; tests unitaires
- `SOURCE.md` à jour (licence, dumps, snapshot_id)

**Dépendances :** contrats gelés uniquement (peut démarrer immédiatement).

---

### (b) Gold set — 150–200 questions, 5 types

**Possède :** `src/rag_juridique/gold/`, `data/gold/`

**Livrables**
- 150–200 questions typées : `direct`, `multi_hop`, `temporal`, `unanswerable`,
  `apparent_contradiction`
- Champs contrats : `expected_article_ids`, `as_of` (temporal), `validated`
- Pipeline generate → auto-filter ; **batch de 40** flaggé pour validation humaine
- Dataset card / SAMPLE_TO_REVIEW mis à jour

**Critères d'acceptation**
- `GoldSet` / `Question` valident `data/gold/questions.json`
- Couverture des 5 `QuestionType` ; unanswerables sans gold ids
- Au moins 40 questions avec procédure de revue humaine documentée
- Pas d'édition de `data/corpus/` (références d'ids en lecture)

**Dépendances :** lecture du corpus (a) pour multi-hop / temporal riches ;
  peut prototyper sur le snapshot MVP en attendant (a).

---

### (c) Retrieval — indexers, rerank, graph, 3 chunkers

**Possède :** `src/rag_juridique/retrieval/`, `src/rag_juridique/corpus/chunking.py`

**Livrables**
- Retrievers : BM25, dense **bge-m3**, hybrid, cross-encoder reranker,
  graph-following sur `CrossRef`
- 3 chunkers (`Chunker`) : fixed-size, per-article, structural + parent context
- Tous exposent `Retriever.retrieve(query, k, as_of=None) -> list[RetrievedChunk]`

**Critères d'acceptation**
- Protocoles `Retriever` / `Chunker` respectés (tests de conformité)
- Configs comparables via `config_id` ; MVP hybrid + fixed-size reste reproductible
- `as_of` accepté (no-op toléré tant que versions absentes)
- Pas de régression CI sur les configs baseline chunk_500 / chunk_1000

**Dépendances :** contrats ; graphe / versions de (a) pour graph + temporal retrieval ;
  gold de (b) pour eval end-to-end (sinon gold MVP).

---

### (d) Metrics & stats — métriques, CIs, gate CI

**Possède :** `src/rag_juridique/metrics/`, gates/rapport dans `src/rag_juridique/eval/`, `reports/`

**Livrables**
- recall@k, nDCG, MRR, citation accuracy
- Faithfulness claim-level via **NLI français local** (complément heuristique)
- Courbe risk-coverage (abstention)
- Bootstrap CIs + tests de significance entre configs
- Gate CI : échec sur **baisse statistiquement significative** (pas seulement seuil fixe)
- Consomme `GenerationRecord` fixtures (génération 7–8B hors CI, une fois)

**Critères d'acceptation**
- Sorties `MetricResult` / `MetricReport` / `PerConfigMetrics`
- Rapport + baseline mis à jour ; CI verte sur fixtures
- Error analysis ventilée par `QuestionType`
- Documenter la procédure de regen fixtures GPU → commit

**Dépendances :** fixtures + configs de (c) ; ventilation par type nécessite gold (b).
  Peut étendre les métriques sur le MVP immédiatement.

---

## Next weekend (après phase 2)

- [ ] **Judilibre** : corpus jurisprudence (CASS / JADE), licence + attribution séparées,
      ids et contrats étendus si besoin (mini-PR d'interfaces)
- [ ] **HF Space** : démo Gradio branchée sur le même harness (lecture corpus + retrieval +
      métriques) ; upload dataset gold si validé

## Court terme (hors agents parallèles)

- [ ] Validation humaine des questions de `data/gold/SAMPLE_TO_REVIEW.md`
- [ ] Remplacer `multilingual-e5-small` par `BAAI/bge-m3` (agent c)
- [ ] Upload du gold set sur Hugging Face (dataset card déjà prête) — *manuel*
