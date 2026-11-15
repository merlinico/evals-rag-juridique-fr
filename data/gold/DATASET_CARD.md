---
language:
  - fr
license: mit
pretty_name: Gold QA — Codes civil / consommation / travail (RAG eval)
task_categories:
  - question-answering
  - text-retrieval
tags:
  - rag
  - legal
  - french
  - evaluation
  - code-civil
  - code-de-la-consommation
  - code-du-travail
  - multi-hop
  - temporal
size_categories:
  - n<1K
---

# Dataset card — Gold QA (codes FR)

Jeux de questions de référence pour évaluer un pipeline RAG sur un **snapshot figé**
des codes civil, de la consommation et du travail (dump LEGI / DILA, Licence Ouverte 2.0).

> Ce fichier est prêt pour un upload Hugging Face ultérieur. **Aucun upload n'a été effectué.**

## Contenu (phase 2, v0.3.4)

- **~180 questions** en français (`data/gold/questions.json`), dont **40** (`REVIEW_BATCH_40`) `validated: true` ; le reste `validated: false`.
- Snapshot corpus : `codes-v0.2-2025-07-13` (`articles.json.gz` + `versions.json.gz` + `crossrefs.json.gz`).
- Correctifs revue : découpage robuste aux abréviations `L./R./D./1°`, CrossRef hors-code filtrés,
  `u02` requalifié (congés payés / L. 3141-3), `ac05` corrigé, batch civil/travail ;
  passe qualité v0.3.4 (réponses mh synthétisées, acteurs par domaine, diffs temporels concrets).
- Cinq types (`QuestionType`) :
  - `direct` — une question, un (ou quelques) article(s) gold ;
  - `multi_hop` — **CrossRef réels** entre articles (≥ 2), codes civil / consommation / travail ;
  - `temporal` — `as_of` où `Corpus.version_at` renvoie une rédaction **différente** du tip ;
  - `unanswerable` — hors snapshot (abstention attendue, sans `expected_article_ids`) ;
  - `apparent_contradiction` — pièges d'apparente antinomie résolus par articulation des textes.
- Pipeline : génération scriptée → auto-filtre (answerability, dédup, leakage) ;
  stats dans `filter_stats.json`.
- **Batch de revue** : `REVIEW_BATCH_40.md` (inclut `SAMPLE_TO_REVIEW.md`).

## Source juridique

Voir `data/corpus/SOURCE.md` : DILA / LEGI, Licence Ouverte 2.0.

Le jeu de questions / réponses de référence est sous licence MIT (ce dépôt).
Les textes d'articles restent sous Licence Ouverte (DILA).

## Régénération

```bash
# Jeu complet (templates MVP + filtres)
uv run python -m rag_juridique.gold.build
# multi_hop + temporal uniquement depuis CrossRef / version_at
uv run python -m rag_juridique.gold.regen_cli
```

## Limitations

- Questions générées pour l'évaluation RAG, **40 validées** (validé par Nicolas Merli, 2026-11-14) ; le reste `validated: false`.
- Ne constitue pas un conseil juridique.
- Les `unanswerable` restent à re-vérifier si le périmètre du snapshot change.
