---
language:
  - fr
license: mit
pretty_name: Gold QA — Code de la consommation (RAG eval)
task_categories:
  - question-answering
  - text-retrieval
tags:
  - rag
  - legal
  - french
  - evaluation
  - code-de-la-consommation
  - multi-hop
  - temporal
size_categories:
  - n<1K
---

# Dataset card — Gold QA (Code de la consommation)

Jeux de questions de référence pour évaluer un pipeline RAG sur un **sous-ensemble figé**
du Code de la consommation (dump LEGI / DILA, Licence Ouverte 2.0).

> Ce fichier est prêt pour un upload Hugging Face ultérieur. **Aucun upload n'a été effectué.**

## Contenu (phase 2)

- **150–200 questions** en français (`data/gold/questions.json`), toutes `validated: false`.
- Cinq types (`QuestionType`) :
  - `direct` — une question, un (ou quelques) article(s) gold ;
  - `multi_hop` — articulation via renvois / citations croisées (≥ 2 articles) ;
  - `temporal` — réponse à une date `as_of` (versions LEGI dès qu'elles sont fournies par le corpus) ;
  - `unanswerable` — hors snapshot (abstention attendue, sans `expected_article_ids`) ;
  - `apparent_contradiction` — pièges d'apparente antinomie résolus par articulation des textes.
- Champs contrats : `expected_article_ids`, `expected_article_nums`, `reference_answer`,
  `as_of`, `validated`, `topic`, `notes`.
- Pipeline : génération scriptée / templates → auto-filtre (answerability, dédup, leakage) ;
  stats dans `filter_stats.json`.
- **Batch de revue humaine** : `REVIEW_BATCH_40.md` (40 questions stratifiées, inclut
  l'échantillon historique `SAMPLE_TO_REVIEW.md`).

## Source juridique

Les articles provenance sont décrits dans `data/corpus/SOURCE.md` :
DILA / LEGI, `Freemium_legi_global_20250713-140000.tar.gz`, Licence Ouverte 2.0.

Le présent jeu de questions / réponses de référence est sous licence MIT (ce dépôt).
Les textes d'articles restent sous Licence Ouverte (DILA).

## Extensibilité corpus

Le pipeline lit le snapshot courant (`load_corpus`). S'ils existent, il consomme aussi :

- `data/corpus/cross_refs.json` (graphe agent corpus) — sinon extraction depuis le texte ;
- `data/corpus/versions.json` (prévu) pour ancrer plus finement les `temporal`.

Régénérer :

```bash
uv run python -m rag_juridique.gold.build
```

## Limitations

- Sous-ensemble non exhaustif du code (MVP consommation ; extensible civil / travail).
- Questions générées pour l'évaluation RAG, **non validées juridiquement** tant que
  `validated: false`.
- Ne constitue pas un conseil juridique.
- Les `unanswerable` hors civil/travail/consommation restent à re-vérifier si le corpus s'étend.
