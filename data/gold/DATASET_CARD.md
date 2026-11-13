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
size_categories:
  - n<1K
---

# Dataset card — Gold QA (Code de la consommation)

Jeux de questions de référence pour évaluer un pipeline RAG sur un **sous-ensemble figé**
du Code de la consommation (dump LEGI / DILA, Licence Ouverte 2.0).

> Ce fichier est prêt pour un upload Hugging Face ultérieur. **Aucun upload n'a été effectué.**

## Contenu

- 30 questions answerable en français, avec `expected_article_ids`, `expected_article_nums`
  et une `reference_answer` courte.
- 5 questions unanswerable (hors corpus) pour tester l'abstention (`je ne sais pas`).
- Champ `validated: false` jusqu'à revue humaine (`SAMPLE_TO_REVIEW.md`).

## Source juridique

Les articles provenance sont décrits dans `data/corpus/SOURCE.md` :
DILA / LEGI, `Freemium_legi_global_20250713-140000.tar.gz`, Licence Ouverte 2.0.

Le présent jeu de questions / réponses de référence est sous licence MIT (ce dépôt).
Les textes d'articles restent sous Licence Ouverte (DILA).

## Limitations

- Sous-ensemble non exhaustif du code.
- Questions générées pour un MVP d'évaluation, non validées juridiquement.
- Ne constitue pas un conseil juridique.
