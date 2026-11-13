# ROADMAP

## Fait (MVP foundations)

- [x] Corpus figé Code de la consommation + attribution Licence Ouverte
- [x] Gold set 30 + 5 unanswerables (`validated: false`)
- [x] Retrieval hybride BM25 + multilingual-e5 + RRF
- [x] Générateur local Qwen2.5 3B (Ollama) + fixtures CI
- [x] Métriques recall@k / abstention / faithfulness heuristique
- [x] Comparaison 2 chunk sizes + rapport markdown
- [x] CI GitHub Actions avec seuils vs baseline

## Prochaines étapes

### Court terme

- [ ] Validation humaine des 10 questions de `data/gold/SAMPLE_TO_REVIEW.md`
- [ ] Remplacer `multilingual-e5-small` par `BAAI/bge-m3` (plus lourd, souvent meilleur en FR)
- [ ] **Reranking cross-encoder** (ex. `BAAI/bge-reranker-v2-m3`) comme 3ᵉ config
- [ ] Upload du gold set sur Hugging Face (dataset card déjà prête) — *manuel*

### Moyen terme

- [ ] Étendre le snapshot (Livre entier / code complet) sans casser les ids gelés
- [ ] NLI léger local pour la faithfulness (complement à l'overlap)
- [ ] Jurisprudence (CASS / JADE) en second corpus, licence et attribution séparées
- [ ] Interface démo (HF Space ou Gradio local) branchée sur le même eval harness

### Plus tard

- [ ] Gold set 50–100 questions validées + inter-annotator agreement
- [ ] Suivi de drift législatif (diff d'articles entre dumps LEGI)
- [ ] Calibration de l'abstention (seuil de score de retrieval)
