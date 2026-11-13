# Rapport de régression RAG — Code de la consommation

Comparaison de configs (fusion hybride BM25 + embeddings) avec métriques phase 2,
intervalles de confiance bootstrap et tests de significance appariés.

Métriques de ranking : **recall@5**, **nDCG@5**, **MRR**.
Citation accuracy : précision des articles cités vs contexte récupéré.
Fidélité : overlap lexical (CI) ; NLI claim-level FR optionnel hors CI.
Abstention : taux correct / fausse abstention + courbe **risk-coverage**.

## Tableau

| Config | chunk | recall@k | nDCG | MRR | citation | faithfulness | abst. OK | fausse abst. | RC-AUC |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| chunk_500 | 500 | 0.950 | 0.832 | 0.803 | 0.921 | 0.886 | 1.000 | 0.200 | 0.119 |
| chunk_1000 | 1000 | 0.967 | 0.897 | 0.873 | 0.824 | 0.771 | 1.000 | 0.067 | 0.101 |

## Intervalles de confiance (bootstrap)

### chunk_500

| Métrique | valeur | IC | n |
|---|---:|---|---:|
| recall_at_k | 0.950 | [0.867, 1.000] | 30 |
| ndcg | 0.832 | [0.731, 0.913] | 30 |
| mrr | 0.803 | [0.703, 0.900] | 30 |
| citation_accuracy | 0.921 | [0.821, 0.993] | 35 |
| faithfulness | 0.886 | [0.771, 0.971] | 35 |
| correct_abstention_rate | 1.000 | [1.000, 1.000] | 5 |
| false_abstention_rate | 0.200 | [0.067, 0.367] | 30 |
| risk_coverage | 0.119 | — | 35 |

### chunk_1000

| Métrique | valeur | IC | n |
|---|---:|---|---:|
| recall_at_k | 0.967 | [0.900, 1.000] | 30 |
| ndcg | 0.897 | [0.800, 0.967] | 30 |
| mrr | 0.873 | [0.773, 0.957] | 30 |
| citation_accuracy | 0.824 | [0.705, 0.929] | 35 |
| faithfulness | 0.771 | [0.629, 0.914] | 35 |
| correct_abstention_rate | 1.000 | [1.000, 1.000] | 5 |
| false_abstention_rate | 0.067 | [0.000, 0.167] | 30 |
| risk_coverage | 0.101 | — | 35 |


## Erreurs par type de question

### chunk_500

| type | n | error_rate | recall | faith | citation | miss retr. | fausse abst. | cite KO |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| direct | 30 | 0.367 | 0.95 | 0.8667 | 0.9083 | 2 | 6 | 4 |
| unanswerable | 5 | 0.000 | — | 1.0 | 1.0 | 0 | 0 | 0 |

### chunk_1000

| type | n | error_rate | recall | faith | citation | miss retr. | fausse abst. | cite KO |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| direct | 30 | 0.333 | 0.9667 | 0.7333 | 0.7944 | 1 | 2 | 8 |
| unanswerable | 5 | 0.000 | — | 1.0 | 1.0 | 0 | 0 | 0 |


## Tests de significance entre configs

Test apparié bootstrap unilatéral : H1 = la config B régresse vs A (mean Δ < 0), α documenté ci-dessous.

| A | B | métrique | mean A | mean B | Δ (B−A) | p | significatif | n |
|---|---|---|---:|---:|---:|---:|---|---:|
| chunk_500 | chunk_1000 | recall_at_k | 0.950 | 0.967 | +0.017 | 0.922 | non | 30 |
| chunk_500 | chunk_1000 | faithfulness | 0.886 | 0.771 | -0.114 | 0.041 | oui | 35 |
| chunk_500 | chunk_1000 | ndcg | 0.832 | 0.897 | +0.065 | 0.985 | non | 30 |
| chunk_500 | chunk_1000 | mrr | 0.803 | 0.873 | +0.071 | 0.966 | non | 30 |


## Commentaire

- Meilleur rappel : **chunk_1000** (0.967).
- Meilleure fidélité : **chunk_500** (0.886).
- Écart de recall@5 (chunk_1000 − chunk_500) : +0.017.
- Les deux chunk sizes sont proches sur ce petit corpus gelé ; des écarts plus nets sont attendus avec un corpus plus large ou un reranker.

## Gate CI (significance)

La CI échoue **uniquement** si une métrique gate (`recall_at_k`, `faithfulness`)
présente une **régression statistiquement significative** vs `baseline_metrics.json`.

- **Test** : bootstrap apparié unilatéral sur scores par question
  (`paired_bootstrap`), H1 : mean(current − baseline) < 0
- **α** : `metrics.significance_alpha` (défaut **0.05**)
- Les seuils absolus fixes (`min_recall_at_k` / `min_faithfulness`) ne sont plus
  utilisés comme critère d'échec.



## Limites

- Jeu d'or non encore validé humainement (`validated: false`).
- Fidélité CI = heuristique overlap ; NLI FR local optionnel (`metrics.nli_enabled`).
- Générateur local : fixtures CI figent ses sorties ; regen 7B hors CI (voir `RUN_ON_GPU.md`).
- Bootstrap sur N≈30 : les IC sont larges ; le gate exige une régression significative.
