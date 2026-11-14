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
| chunk_500 | 500 | 0.483 | 0.432 | 0.446 | 0.562 | 0.556 | 1.000 | 0.046 | 0.315 |
| chunk_1000 | 1000 | 0.483 | 0.441 | 0.454 | 0.544 | 0.533 | 1.000 | 0.020 | 0.313 |

## Intervalles de confiance (bootstrap)

### chunk_500

| Métrique | valeur | IC | n |
|---|---:|---|---:|
| recall_at_k | 0.483 | [0.411, 0.556] | 151 |
| ndcg | 0.432 | [0.362, 0.498] | 151 |
| mrr | 0.446 | [0.374, 0.521] | 151 |
| citation_accuracy | 0.562 | [0.483, 0.635] | 180 |
| faithfulness | 0.556 | [0.483, 0.633] | 180 |
| correct_abstention_rate | 1.000 | [1.000, 1.000] | 29 |
| false_abstention_rate | 0.046 | [0.013, 0.086] | 151 |
| risk_coverage | 0.315 | — | 180 |

### chunk_1000

| Métrique | valeur | IC | n |
|---|---:|---|---:|
| recall_at_k | 0.483 | [0.411, 0.560] | 151 |
| ndcg | 0.441 | [0.370, 0.509] | 151 |
| mrr | 0.454 | [0.379, 0.528] | 151 |
| citation_accuracy | 0.544 | [0.471, 0.615] | 180 |
| faithfulness | 0.533 | [0.461, 0.611] | 180 |
| correct_abstention_rate | 1.000 | [1.000, 1.000] | 29 |
| false_abstention_rate | 0.020 | [0.000, 0.046] | 151 |
| risk_coverage | 0.313 | — | 180 |


## Erreurs par type de question

### chunk_500

| type | n | error_rate | recall | faith | citation | miss retr. | fausse abst. | cite KO |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| apparent_contradiction | 30 | 0.367 | 0.75 | 0.8333 | 0.8333 | 11 | 0 | 5 |
| direct | 51 | 0.314 | 0.8627 | 0.8235 | 0.848 | 7 | 6 | 9 |
| multi_hop | 40 | 0.950 | 0.1375 | 0.075 | 0.075 | 38 | 1 | 37 |
| temporal | 30 | 0.967 | 0.0333 | 0.0333 | 0.0333 | 29 | 0 | 29 |
| unanswerable | 29 | 0.000 | — | 1.0 | 1.0 | 0 | 0 | 0 |

### chunk_1000

| type | n | error_rate | recall | faith | citation | miss retr. | fausse abst. | cite KO |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| apparent_contradiction | 30 | 0.367 | 0.7833 | 0.8667 | 0.8667 | 11 | 0 | 4 |
| direct | 51 | 0.333 | 0.8235 | 0.7059 | 0.7418 | 9 | 2 | 15 |
| multi_hop | 40 | 0.950 | 0.1375 | 0.075 | 0.075 | 37 | 1 | 37 |
| temporal | 30 | 0.933 | 0.0667 | 0.0667 | 0.0667 | 28 | 0 | 28 |
| unanswerable | 29 | 0.000 | — | 1.0 | 1.0 | 0 | 0 | 0 |


## Tests de significance entre configs

Test apparié bootstrap unilatéral : H1 = la config B régresse vs A (mean Δ < 0), α documenté ci-dessous.

| A | B | métrique | mean A | mean B | Δ (B−A) | p | significatif | n |
|---|---|---|---:|---:|---:|---:|---|---:|
| chunk_500 | chunk_1000 | recall_at_k | 0.483 | 0.483 | +0.000 | 0.492 | non | 151 |
| chunk_500 | chunk_1000 | faithfulness | 0.556 | 0.533 | -0.022 | 0.145 | non | 180 |
| chunk_500 | chunk_1000 | ndcg | 0.432 | 0.441 | +0.009 | 0.702 | non | 151 |
| chunk_500 | chunk_1000 | mrr | 0.446 | 0.454 | +0.008 | 0.655 | non | 151 |


## Commentaire

- Meilleur rappel : **chunk_500** (0.483).
- Meilleure fidélité : **chunk_500** (0.556).
- Écart de recall@5 (chunk_1000 − chunk_500) : +0.000.
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

- Jeu d'or partiellement validé humainement (batch 40 `validated: true` ; reste `false`).
- Fidélité CI = heuristique overlap ; NLI FR local optionnel (`metrics.nli_enabled`).
- Générateur local : fixtures CI figent ses sorties ; regen 7B hors CI (voir `RUN_ON_GPU.md`).
- Bootstrap sur N≈30 : les IC sont larges ; le gate exige une régression significative.
